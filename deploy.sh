 #!/bin/bash

# 部署脚本：同步代码并重启Nginx服务
# 用法: ./deploy.sh [源代码目录] [目标网站目录]
# 注意：这个脚本会同步codebase代码到目标网站目录，并重启Nginx服务

# 显示颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 显示带时间戳的日志
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] 错误:${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] 警告:${NC} $1"
}

# 默认参数
SOURCE_DIR="."
DEST_DIR="/var/www/airankingx.com"
NGINX_CONF="/etc/nginx/sites-available/airankingx.com"
NGINX_ENABLED="/etc/nginx/sites-enabled/airankingx.com"
BACKUP_DIR="/var/www/backups/airankingx.com/$(date '+%Y%m%d_%H%M%S')"
SERVER_USER="www-data"
SERVER_GROUP="www-data"
PYTHON_SERVICE="airanking"
CODEBASE_DIR="/home/jerry/codebase/airanking/"

# 解析命令行参数
if [ $# -ge 1 ]; then
    SOURCE_DIR="$1"
fi

if [ $# -ge 2 ]; then
    DEST_DIR="$2"
fi

# 检查是否有sudo权限
if [ "$EUID" -ne 0 ]; then
    warning "此脚本需要管理员权限才能重启Nginx服务"
    warning "使用sudo运行此脚本"
    exit 1
fi

# 开始部署
log "开始部署..."
log "源目录: $SOURCE_DIR"
log "目标目录: $DEST_DIR"

# 1. 创建备份
log "创建网站备份到 $BACKUP_DIR..."
mkdir -p "$BACKUP_DIR"
if [ $? -ne 0 ]; then
    error "无法创建备份目录"
    exit 1
fi

# 备份当前网站文件
if [ -d "$DEST_DIR" ]; then
    cp -r "$DEST_DIR"/* "$BACKUP_DIR"
    log "备份完成"
else
    warning "目标目录不存在，将创建新目录"
    mkdir -p "$DEST_DIR"
fi

# 2. 同步代码(仅同步指定文件)
log "仅同步固定的代码文件到目标目录..."

FILES_TO_SYNC="
airankingx.py
app.js
styles.css
index.html
nginx.conf
player_statistics_251029.csv
team_building_record.csv
player_statistics.csv
deploy.sh
restart_service_only.sh
service_monitor.sh
"

for file in $FILES_TO_SYNC; do
    if [ -f "$SOURCE_DIR/$file" ]; then
        rsync -avz "$SOURCE_DIR/$file" "$DEST_DIR"/
        if [ $? -ne 0 ]; then
            error "文件 $file 同步失败"
            exit 1
        fi
    else
        warning "源目录不存在文件: $file, 跳过"
    fi
done
log "指定代码文件同步完成"

# 3. 设置权限
log "设置文件权限..."
chown -R www-data:www-data "$DEST_DIR"
chmod -R 755 "$DEST_DIR"
# 确保CSV文件可写（包括备份文件）
find "$DEST_DIR" -name "*.csv" -exec chmod 664 {} \;
find "$DEST_DIR" -name "*.csv.bak" -exec chmod 664 {} \; 2>/dev/null || true
# 确保日志文件可写
find "$DEST_DIR" -name "*.log" -exec chmod 664 {} \; 2>/dev/null || true

# 确保 CODEBASE_DIR 对 www-data 可写（airankingx.py 需要回写 CSV）
if [ -d "$CODEBASE_DIR" ]; then
    log "设置 CODEBASE_DIR 权限以允许 www-data 写入..."
    
    # 确保 www-data 是 jerry 组的成员
    if ! groups www-data | grep -q '\bjerry\b'; then
        log "将 www-data 添加到 jerry 组..."
        usermod -a -G jerry www-data
        log "www-data 已加入 jerry 组（需要重启服务生效）"
    else
        log "www-data 已在 jerry 组中"
    fi
    
    # 确保父目录链对 www-data 可访问（需要读和执行权限）
    chmod o+rx /home/jerry 2>/dev/null || true
    chmod o+rx /home/jerry/codebase 2>/dev/null || true
    
    # 设置 CODEBASE_DIR 本身的权限（jerry 用户和组，www-data 通过组成员访问）
    chown -R jerry:jerry "$CODEBASE_DIR"
    chmod -R 775 "$CODEBASE_DIR"
    # 确保 CSV 文件可写（包括备份文件）
    find "$CODEBASE_DIR" -name "*.csv" -exec chmod 664 {} \;
    find "$CODEBASE_DIR" -name "*.csv.bak" -exec chmod 664 {} \; 2>/dev/null || true
    find "$CODEBASE_DIR" -name "*.csv.tmp" -exec chmod 664 {} \; 2>/dev/null || true
    # 确保日志文件可写
    find "$CODEBASE_DIR" -name "*.log" -exec chmod 664 {} \; 2>/dev/null || true
    
    # 验证权限设置
    log "验证 CODEBASE_DIR 权限..."
    ls -ld "$CODEBASE_DIR" >> /dev/null
    if [ $? -eq 0 ]; then
        log "CODEBASE_DIR 权限设置完成"
    else
        warning "CODEBASE_DIR 权限验证失败"
    fi
else
    warning "CODEBASE_DIR 不存在: $CODEBASE_DIR，跳过权限设置"
fi

log "权限设置完成"

# 3.5 重启/验证 Python 服务（airanking）
log "检查并重启Python服务(${PYTHON_SERVICE})..."
if [ ! -f "/etc/systemd/system/${PYTHON_SERVICE}.service" ]; then
    warning "未发现 /etc/systemd/system/${PYTHON_SERVICE}.service，跳过Python服务重启"
else
    systemctl daemon-reload
    systemctl restart ${PYTHON_SERVICE}
    if systemctl is-active --quiet ${PYTHON_SERVICE}; then
        log "Python服务已成功重启"
    else
        warning "Python服务重启失败，尝试手动启动以诊断..."
        (cd "$DEST_DIR" && sudo -u ${SERVER_USER} python3 airankingx.py &)
        PID=$!
        sleep 5
        if kill -0 $PID 2>/dev/null; then
            log "Python服务可手动启动，尝试再次通过systemd启动"
            kill $PID
            systemctl restart ${PYTHON_SERVICE}
            if systemctl is-active --quiet ${PYTHON_SERVICE}; then
                log "Python服务已通过systemd成功重启"
            else
                warning "Python服务仍无法通过systemd启动，请检查 systemctl status ${PYTHON_SERVICE} 和 server.log"
            fi
        else
            error "Python服务无法手动启动，请检查 ${DEST_DIR}/airankingx.py"
        fi
    fi
fi

# 4. 检查Nginx配置
log "检查Nginx配置..."
nginx -t
if [ $? -ne 0 ]; then
    error "Nginx配置测试失败，请检查配置"
    exit 1
fi
log "Nginx配置正常"

# 5. 重启Nginx服务
log "重启Nginx服务..."
systemctl restart nginx
if [ $? -ne 0 ]; then
    error "Nginx重启失败"
    exit 1
fi

# 6. 检查Nginx服务状态
systemctl status nginx | grep "active (running)" > /dev/null
if [ $? -eq 0 ]; then
    log "Nginx服务已成功重启"
else
    error "Nginx服务可能未正常运行，请检查状态"
    systemctl status nginx
    exit 1
fi

log "部署完成！网站已更新并重启服务。"
log "访问 http://airankingx.com 查看更新后的网站"

# 7. 健康检查（可选）
if command -v curl >/dev/null 2>&1; then
    log "执行健康检查..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://airankingx.com)
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
        log "首页可访问，HTTP状态码: $HTTP_CODE"
    else
        warning "首页可能不可访问，HTTP状态码: $HTTP_CODE"
    fi

    API_LEADERBOARD=$(curl -s -o /dev/null -w "%{http_code}" http://airankingx.com/leaderboard)
    if [ "$API_LEADERBOARD" = "200" ]; then
        log "/leaderboard 接口可访问"
    else
        warning "/leaderboard 接口不可访问，HTTP状态码: $API_LEADERBOARD"
    fi

    API_UPDATE=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS http://airankingx.com/update_leaderboard)
    if [ "$API_UPDATE" = "200" ] || [ "$API_UPDATE" = "204" ]; then
        log "/update_leaderboard 预检请求正常 (HTTP $API_UPDATE)"
    else
        warning "/update_leaderboard 预检可能异常，HTTP状态码: $API_UPDATE"
    fi

    # 端口监听检查（8888）
    if command -v ss >/dev/null 2>&1; then
        if ss -tuln | grep -q ":8888 "; then
            log "端口 8888 正在监听"
        else
            warning "未检测到端口 8888 监听，Python服务可能未正常运行"
        fi
    elif command -v netstat >/dev/null 2>&1; then
        if netstat -tuln | grep -q 8888; then
            log "端口 8888 正在监听"
        else
            warning "未检测到端口 8888 监听，Python服务可能未正常运行"
        fi
    else
        warning "未找到 ss/netstat，跳过端口检查"
    fi
else
    warning "未找到 curl，跳过健康检查"
fi

# 8. 检测并设置系统 cron 定时执行 service_monitor.sh
CRON_FILE="/etc/cron.d/airanking_monitor"
MONITOR_SCRIPT_SOURCE="${SOURCE_DIR}/service_monitor.sh"
MONITOR_SCRIPT_TARGET="${DEST_DIR}/service_monitor.sh"

if [ -f "$MONITOR_SCRIPT_SOURCE" ]; then
    log "检测/安装 service_monitor.sh 定时任务..."
    # 确保脚本存在于目标目录
    cp -f "$MONITOR_SCRIPT_SOURCE" "$MONITOR_SCRIPT_TARGET"
    chmod 755 "$MONITOR_SCRIPT_TARGET"
    chown ${SERVER_USER}:${SERVER_GROUP} "$MONITOR_SCRIPT_TARGET"

    # 如果 cron 文件不存在或不包含预期任务，则写入
    NEED_WRITE=0
    if [ ! -f "$CRON_FILE" ]; then
        NEED_WRITE=1
    else
        if ! grep -q "$MONITOR_SCRIPT_TARGET" "$CRON_FILE"; then
            NEED_WRITE=1
        fi
    fi

    if [ $NEED_WRITE -eq 1 ]; then
        log "创建/更新 cron 任务: 每12小时执行 service_monitor.sh"
        echo "0 */12 * * * root /bin/bash ${MONITOR_SCRIPT_TARGET} >> ${DEST_DIR}/logs/monitor_cron.log 2>&1" > "$CRON_FILE"
        chmod 644 "$CRON_FILE"
        # 尝试重载 cron（不同系统服务名不同，尽量兼容）
        systemctl reload cron 2>/dev/null || systemctl reload crond 2>/dev/null || true
    else
        log "已检测到现有 cron 任务，无需更新"
    fi
else
    warning "未找到 ${MONITOR_SCRIPT_SOURCE}，跳过安装 service_monitor 定时任务"
fi