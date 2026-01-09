#!/bin/bash

# 重启 Python 服务器脚本
# 用途：重启 airankingx.py 服务，使其获得最新的组权限

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] 错误:${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] 警告:${NC} $1"
}

# 检查是否有 sudo 权限
if [ "$EUID" -ne 0 ]; then
    error "此脚本需要管理员权限"
    echo "使用: sudo $0"
    exit 1
fi

log "正在查找 Python 服务器进程..."

# 查找进程
PID=$(ps aux | grep "[p]ython.*airankingx.py" | awk '{print $2}')

if [ -z "$PID" ]; then
    warning "未找到运行中的 Python 服务器进程"
    log "尝试启动服务..."
    cd /var/www/airankingx.com
    sudo -u www-data /usr/bin/python3 airankingx.py &
    sleep 2
    NEW_PID=$(ps aux | grep "[p]ython.*airankingx.py" | awk '{print $2}')
    if [ -n "$NEW_PID" ]; then
        log "服务已启动，PID: $NEW_PID"
    else
        error "服务启动失败"
        exit 1
    fi
else
    log "找到进程 PID: $PID"
    log "正在停止服务..."
    kill $PID
    sleep 2
    
    # 确认进程已停止
    if ps -p $PID > /dev/null 2>&1; then
        warning "进程未响应 SIGTERM，使用 SIGKILL..."
        kill -9 $PID
        sleep 1
    fi
    
    log "正在重新启动服务..."
    cd /var/www/airankingx.com
    sudo -u www-data /usr/bin/python3 airankingx.py &
    sleep 2
    
    NEW_PID=$(ps aux | grep "[p]ython.*airankingx.py" | awk '{print $2}')
    if [ -n "$NEW_PID" ]; then
        log "服务已重启，新 PID: $NEW_PID"
        
        # 验证新进程的组成员
        log "验证进程组成员..."
        GROUPS=$(cat /proc/$NEW_PID/status | grep "^Groups:" | awk '{print $2, $3}')
        log "进程组: $GROUPS"
        
        if echo "$GROUPS" | grep -q "1000"; then
            log "✓ 进程已加入 jerry 组 (GID 1000)"
        else
            warning "进程未加入 jerry 组，可能无法写入代码库目录"
        fi
    else
        error "服务重启失败"
        exit 1
    fi
fi

log "完成！"

