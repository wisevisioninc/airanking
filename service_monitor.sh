#!/bin/bash

# 设置颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 设置变量
TARGET_DIR="/var/www/airankingx.com"
SERVER_USER="www-data"
SERVER_GROUP="www-data"
PYTHON_SERVICE="airanking"
LOG_DIR="${TARGET_DIR}/logs"
LOG_FILE="${LOG_DIR}/monitor_$(date +"%Y%m%d").log"
API_ENDPOINT="http://airankingx.com/update_leaderboard"
# 检查间隔改为12小时 (不再需要此变量，由cron控制)

# 确保日志目录存在
mkdir -p "${LOG_DIR}"

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

# 确保使用airankingx.py文件
ensure_python_files() {
  log "检查Python文件..." "INFO"

  # 确保Python文件有正确的权限
  chmod 755 "${TARGET_DIR}"/*.py
  chown "${SERVER_USER}:${SERVER_GROUP}" "${TARGET_DIR}"/*.py
  
  return 0
}

# 检查Python服务状态
check_python_service() {
  log "检查Python服务状态..." "INFO"
  if ! systemctl is-active --quiet ${PYTHON_SERVICE}; then
    log "Python服务不在运行状态，尝试重启..." "WARNING"
    systemctl restart ${PYTHON_SERVICE}
    sleep 5
    
    if ! systemctl is-active --quiet ${PYTHON_SERVICE}; then
      log "Python服务重启失败，检查服务配置..." "ERROR"
      
      # 检查systemd服务文件是否正确指向Python文件
      EXEC_START=$(systemctl cat ${PYTHON_SERVICE} | grep "ExecStart" | awk -F '=' '{print $2}')
      log "当前ExecStart配置: ${EXEC_START}" "INFO"
      
      # 确保文件名正确
      ensure_python_files
      
      # 重新加载systemd并再次尝试重启
      systemctl daemon-reload
      systemctl restart ${PYTHON_SERVICE}
      sleep 5
      
      if ! systemctl is-active --quiet ${PYTHON_SERVICE}; then
        log "Python服务仍然无法启动，查看日志..." "ERROR"
        journalctl -u ${PYTHON_SERVICE} -n 20 --no-pager >> "${LOG_FILE}"
        return 1
      else
        log "Python服务成功重启" "INFO"
      fi
    else
      log "Python服务成功重启" "INFO"
    fi
  else
    log "Python服务运行正常" "INFO"
  fi
  
  return 0
}

# 检查Nginx状态
check_nginx() {
  log "检查Nginx状态..." "INFO"
  if ! systemctl is-active --quiet nginx; then
    log "Nginx不在运行状态，尝试重启..." "WARNING"
    systemctl restart nginx
    sleep 3
    
    if ! systemctl is-active --quiet nginx; then
      log "Nginx重启失败，检查配置..." "ERROR"
      nginx -t >> "${LOG_FILE}" 2>&1
      return 1
    else
      log "Nginx成功重启" "INFO"
    fi
  else
    log "Nginx运行正常" "INFO"
  fi
  
  return 0
}

# 检查API可访问性
check_api_endpoint() {
  log "检查API可访问性..." "INFO"
  
  # 使用curl测试API
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS ${API_ENDPOINT})
  
  if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    log "API端点可访问，HTTP状态码: ${HTTP_CODE}" "INFO"
    return 0
  else
    log "API端点不可访问，HTTP状态码: ${HTTP_CODE}" "ERROR"
    
    # 尝试直接访问Python服务
    DIRECT_API="http://airankingx.com/update_leaderboard"
    DIRECT_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS ${DIRECT_API})
    log "直接访问Python服务API: ${DIRECT_CODE}" "INFO"
    
    # 检查端口是否在监听
    netstat -tuln | grep 8888 >> "${LOG_FILE}"
    
    return 1
  fi
}

# 全面修复
fix_service() {
  log "开始全面修复服务..." "INFO"
  
  # 确保Python文件存在且有正确的权限
  ensure_python_files || return 1
  
  # 检查并修复Python服务
  check_python_service || return 1
  
  # 检查并修复Nginx
  check_nginx || return 1
  
  # 最后检查API可访问性
  if check_api_endpoint; then
    log "服务全面修复成功，API可访问" "INFO"
    return 0
  else
    log "服务全面修复后API仍不可访问，可能需要更深入的调查" "ERROR"
    return 1
  fi
}

# 主函数
log "服务监控开始执行" "INFO"

# 检查Python服务
if ! check_python_service; then
  log "Python服务检查失败，尝试全面修复..." "WARNING"
  fix_service
fi

# 检查Nginx
if ! check_nginx; then
  log "Nginx检查失败，尝试全面修复..." "WARNING"
  fix_service
fi

# 检查API可访问性
if ! check_api_endpoint; then
  log "API检查失败，尝试全面修复..." "WARNING"
  fix_service
fi

log "监控检查完成" "INFO"
exit 0 