#!/bin/bash
# 这个脚本用于重启airankingx.com服务，只重启Python服务和Nginx，不进行部署

# 设置颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 设置变量
TARGET_DIR="/var/www/airankingx.com"
SERVER_USER="www-data"
SERVER_GROUP="www-data"
NGINX_CONF="/etc/nginx/sites-available/airankingx.com"
NGINX_ENABLED="/etc/nginx/sites-enabled/airankingx.com"
PYTHON_SERVICE="airanking"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/restart_${TIMESTAMP}.log"

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

# 记录日志的函数
log() {
  local message="$1"
  local level="$2"
  local color="${NC}"
  
  case "$level" in
    "INFO") color="${GREEN}" ;;
    "ERROR") color="${RED}" ;;
    "WARNING") color="${YELLOW}" ;;
  esac
  
  echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${color}${level}${NC}: ${message}"
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] ${level}: ${message}" >> "${LOG_FILE}"
}

# 检查是否以root权限运行
if [[ $EUID -ne 0 ]]; then
   log "此脚本必须以root权限运行" "ERROR"
   echo "用法: sudo $0"
   exit 1
fi

# 开始重启流程
log "开始重启airankingx.com服务" "INFO"

# 1. 检查Python服务配置文件是否存在
log "检查Python服务配置..." "INFO"
if [ ! -f "/etc/systemd/system/${PYTHON_SERVICE}.service" ]; then
  log "Python服务配置不存在，请先运行deploy.sh部署服务" "ERROR"
  exit 1
fi

# 2. 检查Python文件
if [ -f "${TARGET_DIR}/server.py" ] && [ ! -f "${TARGET_DIR}/airankingx.py" ]; then
  log "检测到server.py但没有找到airankingx.py，创建软链接..." "WARNING"
  ln -sf "${TARGET_DIR}/server.py" "${TARGET_DIR}/airankingx.py"
  log "已创建软链接" "INFO"
fi

# 3. 重启Python服务
log "重启Python服务..." "INFO"
systemctl daemon-reload
systemctl restart ${PYTHON_SERVICE}

# 检查Python服务状态
if systemctl is-active --quiet ${PYTHON_SERVICE}; then
  log "Python服务已成功重启" "INFO"
else
  log "Python服务重启失败，显示详细日志..." "ERROR"
  log "系统日志:" "INFO"
  journalctl -u ${PYTHON_SERVICE} -n 50 --no-pager >> "${LOG_FILE}"
  
  log "检查权限:" "INFO"
  ls -la "${TARGET_DIR}"/airankingx.py "${TARGET_DIR}"/server*.log >> "${LOG_FILE}"
  
  systemctl status ${PYTHON_SERVICE} --no-pager
  
  # 尝试手动启动Python服务
  log "尝试手动运行Python服务:" "INFO"
  cd "${TARGET_DIR}" && sudo -u ${SERVER_USER} python3 airankingx.py &
  PID=$!
  sleep 5
  if kill -0 $PID 2>/dev/null; then
    log "Python服务可以手动启动，尝试再次通过systemd启动" "INFO"
    kill $PID
    systemctl restart ${PYTHON_SERVICE}
    if ! systemctl is-active --quiet ${PYTHON_SERVICE}; then
      log "仍然无法通过systemd启动Python服务" "ERROR"
    fi
  else
    log "Python服务无法手动启动，请检查Python代码" "ERROR"
  fi
fi

# 4. 重启Nginx
log "重启Nginx..." "INFO"
nginx -t >> "${LOG_FILE}" 2>&1
if [ $? -eq 0 ]; then
  log "Nginx配置有效，准备重启" "INFO"
  systemctl restart nginx
  if [ $? -eq 0 ]; then
    log "Nginx重启成功" "INFO"
  else
    log "Nginx重启失败" "ERROR"
    systemctl status nginx --no-pager
    exit 1
  fi
else
  log "Nginx配置无效，请检查配置文件" "ERROR"
  cat "${LOG_FILE}"
  exit 1
fi

# 5. 检查是否所有服务都在运行
log "检查服务状态..." "INFO"
if systemctl is-active --quiet nginx && systemctl is-active --quiet ${PYTHON_SERVICE}; then
  log "所有服务都在正常运行" "INFO"
else
  log "一个或多个服务未正常运行，请检查系统日志" "ERROR"
  exit 1
fi

# 6. 检查服务是否可访问
log "检查服务可访问性..." "INFO"
if command -v curl &> /dev/null; then
  log "使用curl检查网站可访问性..." "INFO"
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost)
  if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
    log "网站服务可访问，HTTP状态码: ${HTTP_CODE}" "INFO"
  else
    log "网站服务可能不可访问，HTTP状态码: ${HTTP_CODE}" "WARNING"
  fi
  
  # 检查API端点
  log "检查API端点可访问性..." "INFO"
  API_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS http://localhost/update_game_data)
  if [ "$API_CODE" = "200" ] || [ "$API_CODE" = "204" ]; then
    log "API端点可访问，HTTP状态码: ${API_CODE}" "INFO"
  else
    log "API端点可能不可访问，HTTP状态码: ${API_CODE}" "WARNING"
  fi
else
  log "未找到curl命令，跳过可访问性检查" "WARNING"
fi

# 7. 清理和查看相关日志
log "清理和查看相关日志..." "INFO"

# 清空或截断JavaScript控制台日志（如果前端调试开启）
if [ -f "${TARGET_DIR}/console.log" ]; then
  log "清空JavaScript控制台日志..." "INFO"
  echo "" > "${TARGET_DIR}/console.log"
fi

# 保留最近的Python服务日志
if [ -f "${TARGET_DIR}/server.log" ] && [ $(wc -l < "${TARGET_DIR}/server.log") -gt 10000 ]; then
  log "截断过长的Python服务日志..." "INFO"
  tail -n 5000 "${TARGET_DIR}/server.log" > "${TARGET_DIR}/server.log.tmp"
  mv "${TARGET_DIR}/server.log.tmp" "${TARGET_DIR}/server.log"
  chown "${SERVER_USER}:${SERVER_GROUP}" "${TARGET_DIR}/server.log"
  chmod 664 "${TARGET_DIR}/server.log"
fi

# 显示最近的Python服务日志
log "显示最近的Python服务日志（最后10行）:" "INFO"
if [ -f "${TARGET_DIR}/server.log" ]; then
  tail -n 10 "${TARGET_DIR}/server.log" >> "${LOG_FILE}"
else
  log "未找到Python服务日志文件" "WARNING"
fi

# 显示最近的nginx日志
log "显示最近的Nginx错误日志（最后10行）:" "INFO"
if [ -f "/var/log/nginx/error.log" ]; then
  tail -n 10 "/var/log/nginx/error.log" >> "${LOG_FILE}"
else
  log "未找到Nginx错误日志文件" "WARNING"
fi

# 检查CSV文件权限
log "检查数据文件权限:" "INFO"
ls -la "${TARGET_DIR}"/*.csv >> "${LOG_FILE}"

# 重启完成
log "重启完成! airankingx.com服务已重启" "INFO"
echo -e "${GREEN}重启成功!${NC} 查看详细日志: ${LOG_FILE}" 