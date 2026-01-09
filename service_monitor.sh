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

# 确保使用airankingx.py文件和相关权限
ensure_python_files() {
  log "检查Python文件和权限..." "INFO"

  # 确保Python文件有正确的权限
  chmod 755 "${TARGET_DIR}"/*.py 2>/dev/null || true
  chown "${SERVER_USER}:${SERVER_GROUP}" "${TARGET_DIR}"/*.py 2>/dev/null || true
  
  # 确保CSV文件可写（包括备份文件和临时文件）
  find "${TARGET_DIR}" -name "*.csv" -exec chmod 664 {} \; 2>/dev/null || true
  find "${TARGET_DIR}" -name "*.csv.bak" -exec chmod 664 {} \; 2>/dev/null || true
  find "${TARGET_DIR}" -name "*.csv.tmp" -exec chmod 664 {} \; 2>/dev/null || true
  find "${TARGET_DIR}" -name "*.csv" -exec chown ${SERVER_USER}:${SERVER_GROUP} {} \; 2>/dev/null || true
  find "${TARGET_DIR}" -name "*.csv.bak" -exec chown ${SERVER_USER}:${SERVER_GROUP} {} \; 2>/dev/null || true
  
  # 确保日志目录存在且可写
  mkdir -p "${TARGET_DIR}/logs" 2>/dev/null || true
  chown -R ${SERVER_USER}:${SERVER_GROUP} "${TARGET_DIR}/logs" 2>/dev/null || true
  chmod 775 "${TARGET_DIR}/logs" 2>/dev/null || true
  
  # 确保所有日志文件有正确权限
  find "${TARGET_DIR}" -name "*.log" -exec chmod 664 {} \; 2>/dev/null || true
  find "${TARGET_DIR}" -name "*.log" -exec chown ${SERVER_USER}:${SERVER_GROUP} {} \; 2>/dev/null || true
  
  # 确保 CODEBASE_DIR 权限正确（关键！）
  CODEBASE_DIR="/home/jerry/codebase/airanking/"
  if [ -d "$CODEBASE_DIR" ]; then
    log "检查 CODEBASE_DIR 权限..." "INFO"
    
    # 确保 www-data 在 jerry 组中
    if ! groups www-data | grep -q '\bjerry\b'; then
      log "www-data 不在 jerry 组，尝试添加..." "WARNING"
      usermod -a -G jerry www-data 2>/dev/null || true
    fi
    
    # 确保父目录可访问
    chmod o+rx /home/jerry 2>/dev/null || true
    chmod o+rx /home/jerry/codebase 2>/dev/null || true
    
    # 设置 CODEBASE_DIR 权限
    chown -R jerry:jerry "$CODEBASE_DIR" 2>/dev/null || true
    chmod -R 775 "$CODEBASE_DIR" 2>/dev/null || true
    # 确保所有CSV相关文件可写
    find "$CODEBASE_DIR" -name "*.csv" -exec chmod 664 {} \; 2>/dev/null || true
    find "$CODEBASE_DIR" -name "*.csv.bak" -exec chmod 664 {} \; 2>/dev/null || true
    find "$CODEBASE_DIR" -name "*.csv.tmp" -exec chmod 664 {} \; 2>/dev/null || true
    # 确保日志文件可写
    find "$CODEBASE_DIR" -name "*.log" -exec chmod 664 {} \; 2>/dev/null || true
    
    log "CODEBASE_DIR 权限检查完成" "INFO"
  else
    log "CODEBASE_DIR 不存在: $CODEBASE_DIR" "WARNING"
  fi
  
  return 0
}

# 检查Python服务状态
check_python_service() {
  log "检查Python服务状态..." "INFO"
  
  # 检查服务是否运行
  if ! systemctl is-active --quiet ${PYTHON_SERVICE}; then
    log "Python服务不在运行状态，尝试重启..." "WARNING"
    
    # 确保 www-data 在 jerry 组中
    if ! groups www-data | grep -q '\bjerry\b'; then
      log "www-data 不在 jerry 组，添加中..." "WARNING"
      usermod -a -G jerry www-data
      log "已将 www-data 添加到 jerry 组" "INFO"
    fi
    
    # 重新加载 systemd 配置
    systemctl daemon-reload
    
    # 重启服务
    systemctl restart ${PYTHON_SERVICE}
    sleep 5
    
    if ! systemctl is-active --quiet ${PYTHON_SERVICE}; then
      log "Python服务重启失败，检查服务配置..." "ERROR"
      
      # 检查systemd服务文件是否正确指向Python文件
      EXEC_START=$(systemctl cat ${PYTHON_SERVICE} | grep "ExecStart" | awk -F '=' '{print $2}')
      log "当前ExecStart配置: ${EXEC_START}" "INFO"
      
      # 确保文件名正确
      ensure_python_files
      
      # 再次尝试重启
      systemctl daemon-reload
      systemctl restart ${PYTHON_SERVICE}
      sleep 5
      
      if ! systemctl is-active --quiet ${PYTHON_SERVICE}; then
        log "Python服务仍然无法启动，查看日志..." "ERROR"
        journalctl -u ${PYTHON_SERVICE} -n 20 --no-pager >> "${LOG_FILE}"
        return 1
      else
        log "Python服务成功重启" "INFO"
        verify_service_permissions
      fi
    else
      log "Python服务成功重启" "INFO"
      verify_service_permissions
    fi
  else
    log "Python服务运行正常" "INFO"
    # 即使服务运行，也验证权限
    verify_service_permissions
  fi
  
  return 0
}

# 验证服务权限
verify_service_permissions() {
  log "验证Python服务权限..." "INFO"
  
  # 获取进程PID
  PID=$(systemctl show -p MainPID ${PYTHON_SERVICE} | cut -d= -f2)
  
  if [ "$PID" = "0" ] || [ -z "$PID" ]; then
    log "无法获取Python服务PID" "WARNING"
    return 1
  fi
  
  # 检查进程的组成员
  if [ -f "/proc/$PID/status" ]; then
    GROUPS=$(cat /proc/$PID/status | grep "^Groups:" | awk '{print $2, $3}')
    log "进程 PID $PID 的组: $GROUPS" "INFO"
    
    # 检查是否包含 jerry 组 (GID 1000)
    if echo "$GROUPS" | grep -q "1000"; then
      log "✓ 进程已加入 jerry 组，可以写入代码库" "INFO"
      return 0
    else
      log "⚠️ 进程未加入 jerry 组，无法写入代码库！需要重启服务" "WARNING"
      
      # 确保 www-data 在 jerry 组中
      if ! groups www-data | grep -q '\bjerry\b'; then
        log "添加 www-data 到 jerry 组..." "INFO"
        usermod -a -G jerry www-data
      fi
      
      # 重启服务以获得新的组权限
      log "重启服务以刷新组权限..." "INFO"
      systemctl daemon-reload
      systemctl restart ${PYTHON_SERVICE}
      sleep 5
      
      # 再次验证
      NEW_PID=$(systemctl show -p MainPID ${PYTHON_SERVICE} | cut -d= -f2)
      if [ -f "/proc/$NEW_PID/status" ]; then
        NEW_GROUPS=$(cat /proc/$NEW_PID/status | grep "^Groups:" | awk '{print $2, $3}')
        if echo "$NEW_GROUPS" | grep -q "1000"; then
          log "✓ 重启后进程已获得 jerry 组权限" "INFO"
          return 0
        else
          log "❌ 重启后进程仍未获得 jerry 组权限" "ERROR"
          return 1
        fi
      fi
    fi
  else
    log "无法读取进程状态文件" "WARNING"
    return 1
  fi
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

# 清理旧日志文件
cleanup_old_logs() {
  log "清理旧日志文件..." "INFO"
  
  # 清理7天前的监控日志
  find "${LOG_DIR}" -name "monitor_*.log" -mtime +7 -delete 2>/dev/null || true
  
  # 如果 server.log 过大（超过100MB），截断保留最后10000行
  if [ -f "${TARGET_DIR}/server.log" ]; then
    LOG_SIZE=$(stat -f%z "${TARGET_DIR}/server.log" 2>/dev/null || stat -c%s "${TARGET_DIR}/server.log" 2>/dev/null || echo 0)
    if [ "$LOG_SIZE" -gt 104857600 ]; then
      log "server.log 过大 (${LOG_SIZE} bytes)，正在截断..." "INFO"
      tail -n 10000 "${TARGET_DIR}/server.log" > "${TARGET_DIR}/server.log.tmp"
      mv "${TARGET_DIR}/server.log.tmp" "${TARGET_DIR}/server.log"
      chown ${SERVER_USER}:${SERVER_GROUP} "${TARGET_DIR}/server.log"
      chmod 664 "${TARGET_DIR}/server.log"
    fi
  fi
}

# 主函数
log "服务监控开始执行" "INFO"

# 清理旧日志
cleanup_old_logs

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