# AIRanking - Team Building Game Score System

团队建设游戏积分排行榜系统

---

## 📋 目录

- [系统概述](#系统概述)
- [系统架构](#系统架构)
- [权限配置详解](#权限配置详解)
- [快速开始](#快速开始)
- [完整部署流程](#完整部署流程)
- [定时任务流程](#定时任务流程)
- [权限问题完全解决方案](#权限问题完全解决方案)
- [日常运维](#日常运维)
- [故障排查](#故障排查)
- [工具脚本说明](#工具脚本说明)
- [文件结构](#文件结构)
- [常见问题](#常见问题)

---

## 系统概述

AIRanking 是一个基于 Python 的 Web 应用，用于管理和展示团队建设游戏的积分排行榜。

### 核心功能

- 📊 实时排行榜展示
- ➕ 新游戏记录录入
- 🧮 自动计算玩家统计
- 📈 历史记录查询
- 🔄 双向数据同步（生产环境 ↔ 代码库）

### 技术栈

- **后端**: Python 3 (http.server)
- **前端**: HTML + JavaScript + CSS
- **Web 服务器**: Nginx (反向代理)
- **服务管理**: systemd
- **定时任务**: cron

---

## 系统架构

### 目录结构

```
生产环境: /var/www/airankingx.com/
├── airankingx.py           # Python 服务器
├── index.html              # 前端页面
├── app.js                  # 前端逻辑
├── styles.css              # 样式文件
├── team_building_record.csv      # 游戏记录
├── player_statistics.csv         # 玩家统计
├── player_statistics_251029.csv  # 基线数据
├── server.log              # 服务器日志
└── logs/                   # 监控日志

代码库: /home/jerry/codebase/airanking/
├── airankingx.py           # 源代码
├── app.js
├── index.html
├── *.csv                   # CSV 数据文件
├── *.sh                    # 工具脚本
├── airanking.service       # systemd 配置
└── *.md                    # 文档
```

### 服务架构

```
用户浏览器
    ↓
Nginx (80端口)
    ↓ 代理 /update_leaderboard
Python 服务 (8888端口)
    ↓ 读写
CSV 文件 (生产环境)
    ↓ 同步
CSV 文件 (代码库)
```

### 用户和权限

| 用户 | UID/GID | 组成员 | 用途 |
|------|---------|--------|------|
| jerry | 1000/1000 | jerry, sudo | 开发用户，代码库所有者 |
| www-data | 33/33 | www-data, jerry | Web 服务用户，运行 Python 服务 |

---

## 权限配置详解

### ⚠️ 权限问题的根源

**核心问题**: Python 服务需要同时写入两个目录：
1. `/var/www/airankingx.com/` (www-data 所有)
2. `/home/jerry/codebase/airanking/` (jerry 所有)

**传统方案的问题**:
- 仅将 www-data 加入 jerry 组不够
- 进程启动时没有获得补充组权限
- 需要重启才能刷新组成员身份

### ✅ 完整解决方案

#### 1. systemd 服务配置（关键！）

**文件**: `/etc/systemd/system/airanking.service`

```ini
[Service]
User=www-data
Group=www-data
SupplementaryGroups=jerry  # ← 关键配置！确保进程获得 jerry 组权限
```

**作用**: 
- 进程启动时自动获得 jerry 组权限
- 无需手动干预
- 解决权限问题的根源

#### 2. 用户组配置

```bash
# www-data 必须在 jerry 组中
usermod -a -G jerry www-data

# 验证
groups www-data
# 输出: www-data : www-data jerry
```

#### 3. 目录权限

```bash
# 父目录 - 允许其他用户访问
/home/jerry/                     755 (drwxr-xr-x)  jerry:jerry
/home/jerry/codebase/            755 (drwxr-xr-x)  jerry:jerry

# 代码库 - jerry 组可写
/home/jerry/codebase/airanking/  775 (drwxrwxr-x)  jerry:jerry

# 生产环境 - www-data 所有
/var/www/airankingx.com/         755 (drwxr-xr-x)  www-data:www-data
```

#### 4. 文件权限

```bash
# CSV 文件 - 组可写
*.csv                            664 (rw-rw-r--)

# Python 文件
生产环境: *.py                   755 (rwxr-xr-x)
代码库: *.py                     664 (rw-rw-r--)

# Shell 脚本
*.sh                             775 (rwxrwxr-x)
```

### 验证权限配置

```bash
# 1. 检查用户组
groups www-data
# 应包含: jerry

# 2. 检查服务配置
grep "SupplementaryGroups" /etc/systemd/system/airanking.service
# 应显示: SupplementaryGroups=jerry

# 3. 检查进程权限
PID=$(systemctl show -p MainPID airanking | cut -d= -f2)
cat /proc/$PID/status | grep "^Groups:"
# 应包含: 33 1000 (www-data 组和 jerry 组)

# 4. 测试写入权限
sudo -u www-data touch /home/jerry/codebase/airanking/.test
# 应该成功
```

---

## 快速开始

### 一键部署和修复

```bash
cd /home/jerry/codebase/airanking
sudo ./deploy.sh
```

### 验证系统状态

```bash
# 运行完整诊断
sudo ./diagnose_system.sh

# 查看日志
./view_logs.sh updates
```

### 测试网站功能

1. 访问: http://airankingx.com
2. 登录 (密码: 88888)
3. 输入新游戏记录
4. 更新榜单
5. 验证成功

---

## 完整部署流程

### 步骤 1: 准备工作

```bash
# 切换到代码库目录
cd /home/jerry/codebase/airanking

# 确保所有脚本可执行
chmod +x *.sh
```

### 步骤 2: 运行部署脚本

```bash
sudo ./deploy.sh
```

### 部署脚本执行的操作

1. **创建备份**
   - 备份 `/var/www/airankingx.com/` 到 `/var/www/backups/airankingx.com/`

2. **同步代码文件**
   ```
   airankingx.py
   app.js
   styles.css
   index.html
   *.csv
   *.sh
   ```

3. **部署 systemd 服务配置**
   - 复制 `airanking.service` 到 `/etc/systemd/system/`
   - 包含关键的 `SupplementaryGroups=jerry` 配置

4. **设置权限**
   - 生产环境: `chown -R www-data:www-data /var/www/airankingx.com`
   - 代码库: `chown -R jerry:jerry /home/jerry/codebase/airanking`
   - CSV 文件: `chmod 664 *.csv`

5. **确保用户组成员**
   - 将 www-data 添加到 jerry 组
   - 验证组成员身份

6. **重启服务**
   - `systemctl daemon-reload`
   - `systemctl restart airanking`
   - 验证进程权限

7. **健康检查**
   - 检查端口监听 (8888)
   - 测试 API 端点
   - 验证文件权限

### 步骤 3: 验证部署

```bash
# 运行诊断
sudo ./diagnose_system.sh

# 期望输出
✓ 未发现严重问题！系统配置正常
```

### 步骤 4: 测试功能

```bash
# 查看服务状态
systemctl status airanking

# 查看日志
./view_logs.sh all -n 50

# 测试网站
curl http://localhost:8888/leaderboard
```

---

## 定时任务流程

### 定时任务配置

**文件**: `/etc/cron.d/airanking_monitor`

**当前配置**:
```cron
0 * * * * root /bin/bash /var/www/airankingx.com/service_monitor.sh >> /var/www/airankingx.com/logs/monitor_cron.log 2>&1
```

**执行频率**: 每小时一次

**建议配置** (减少不必要的重启):
```cron
0 */12 * * * root /bin/bash /var/www/airankingx.com/service_monitor.sh >> /var/www/airankingx.com/logs/monitor_cron.log 2>&1
```

### 定时任务执行流程

#### 1. 检查并修复文件权限

```bash
ensure_python_files() {
  # 设置 Python 文件权限
  chmod 755 ${TARGET_DIR}/*.py
  chown ${SERVER_USER}:${SERVER_GROUP} ${TARGET_DIR}/*.py
  
  # 设置 CSV 文件权限
  find ${TARGET_DIR} -name "*.csv*" -exec chmod 664 {} \;
  find ${TARGET_DIR} -name "*.csv*" -exec chown ${SERVER_USER}:${SERVER_GROUP} {} \;
  
  # 设置代码库权限
  chown -R jerry:jerry /home/jerry/codebase/airanking
  chmod -R 775 /home/jerry/codebase/airanking
  find /home/jerry/codebase/airanking -name "*.csv*" -exec chmod 664 {} \;
}
```

#### 2. 检查 Python 服务状态

```bash
check_python_service() {
  if ! systemctl is-active --quiet airanking; then
    # 服务未运行，重启
    
    # 确保 www-data 在 jerry 组中
    usermod -a -G jerry www-data
    
    # 重新加载配置
    systemctl daemon-reload
    
    # 重启服务
    systemctl restart airanking
  else
    # 服务运行中，验证权限
    verify_service_permissions
  fi
}
```

#### 3. 验证服务权限

```bash
verify_service_permissions() {
  # 获取进程 PID
  PID=$(systemctl show -p MainPID airanking | cut -d= -f2)
  
  # 检查进程组
  GROUPS=$(cat /proc/$PID/status | grep "^Groups:")
  
  # 验证是否包含 jerry 组 (GID 1000)
  if ! echo "$GROUPS" | grep -q "1000"; then
    # 权限不正确，重启服务
    systemctl restart airanking
  fi
}
```

#### 4. 检查 Nginx 状态

```bash
check_nginx() {
  if ! systemctl is-active --quiet nginx; then
    systemctl restart nginx
  fi
}
```

#### 5. 检查 API 可访问性

```bash
check_api_endpoint() {
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS http://airankingx.com/update_leaderboard)
  
  if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "204" ]; then
    # API 不可访问，执行全面修复
    fix_service
  fi
}
```

### 定时任务确保的事项

✅ **文件权限正确**
- 生产环境文件 www-data 可写
- 代码库文件 jerry 组可写

✅ **服务运行正常**
- Python 服务持续运行
- Nginx 服务持续运行

✅ **进程权限正确**
- www-data 进程在 jerry 组中
- 可以写入代码库目录

✅ **API 可访问**
- 端点响应正常
- 网站功能正常

### 查看定时任务日志

```bash
# 查看今天的监控日志
tail -f /var/www/airankingx.com/logs/monitor_$(date +%Y%m%d).log

# 查看 cron 执行日志
tail -f /var/www/airankingx.com/logs/monitor_cron.log

# 查看最近 7 天的监控日志
ls -lt /var/www/airankingx.com/logs/monitor_*.log
```

---

## 权限问题完全解决方案

### 问题症状

- ❌ 更新榜单失败
- ❌ 日志显示 "Permission denied"
- ❌ 文件同步到代码库失败
- ❌ 定时任务后网站出错

### 根本原因

1. **systemd 服务配置不完整**
   - 缺少 `SupplementaryGroups=jerry`
   - 进程无法获得 jerry 组权限

2. **进程未刷新组权限**
   - 即使 www-data 在 jerry 组中
   - 旧进程不会自动获得新权限

3. **部署流程不完整**
   - 没有部署 systemd 配置
   - 没有验证权限状态

### 解决方案

#### 方案 A: 一键修复（推荐）

```bash
cd /home/jerry/codebase/airanking
sudo ./deploy.sh
```

#### 方案 B: 仅修复权限

```bash
sudo ./fix_permissions.sh
```

#### 方案 C: 手动修复

```bash
# 1. 确保 www-data 在 jerry 组中
sudo usermod -a -G jerry www-data

# 2. 更新 systemd 配置
sudo cp /home/jerry/codebase/airanking/airanking.service /etc/systemd/system/

# 3. 设置权限
sudo chown -R jerry:jerry /home/jerry/codebase/airanking
sudo chmod 775 /home/jerry/codebase/airanking
sudo find /home/jerry/codebase/airanking -name "*.csv" -exec chmod 664 {} \;

# 4. 重启服务
sudo systemctl daemon-reload
sudo systemctl restart airanking

# 5. 验证权限
PID=$(systemctl show -p MainPID airanking | cut -d= -f2)
cat /proc/$PID/status | grep "^Groups:"
# 应包含: 33 1000
```

### 验证修复结果

```bash
# 1. 运行完整诊断
sudo ./diagnose_system.sh

# 2. 测试写入权限
sudo -u www-data touch /home/jerry/codebase/airanking/.test
sudo -u www-data rm /home/jerry/codebase/airanking/.test

# 3. 测试网站功能
# 访问网站，更新榜单

# 4. 查看日志
./view_logs.sh updates
# 应看到: ✓ Successfully synced ... to codebase
```

---

## 日常运维

### 每天

```bash
# 查看日志统计
./view_logs.sh stats

# 查看最近的错误
./view_logs.sh errors
```

### 每周

```bash
# 运行系统诊断
sudo ./diagnose_system.sh

# 检查同步状态
./check_sync_status.sh
```

### 每月

```bash
# 归档日志
sudo cp /var/www/airankingx.com/server.log \
        /var/www/airankingx.com/logs/server.log.$(date +%Y%m).bak

# 备份 CSV 文件
sudo cp /var/www/airankingx.com/*.csv \
        /var/www/airankingx.com/logs/backup_$(date +%Y%m%d)/
```

### 部署新代码

```bash
# 1. 在代码库编辑代码
cd /home/jerry/codebase/airanking
# 编辑文件...

# 2. 部署
sudo ./deploy.sh

# 3. 验证
sudo ./diagnose_system.sh

# 4. 测试
# 访问网站测试功能

# 5. 查看日志
./view_logs.sh all -n 50
```

---

## 故障排查

### 问题 1: 更新榜单失败

**症状**:
```
API Error: Load failed
```

**排查步骤**:

```bash
# 1. 查看最近的错误
./view_logs.sh errors

# 2. 检查服务状态
systemctl status airanking

# 3. 运行诊断
sudo ./diagnose_system.sh

# 4. 检查进程权限
PID=$(systemctl show -p MainPID airanking | cut -d= -f2)
cat /proc/$PID/status | grep "^Groups:"
```

**解决方案**:

```bash
# 运行权限修复
sudo ./fix_permissions.sh
```

### 问题 2: 文件同步失败

**症状**:
```
⚠️ Failed to sync to codebase (non-critical): Permission denied
```

**排查步骤**:

```bash
# 1. 检查用户组
groups www-data

# 2. 检查目录权限
ls -ld /home/jerry/codebase/airanking

# 3. 测试写入权限
sudo -u www-data touch /home/jerry/codebase/airanking/.test
```

**解决方案**:

```bash
# 1. 确保 www-data 在 jerry 组中
sudo usermod -a -G jerry www-data

# 2. 重启服务
sudo systemctl restart airanking

# 3. 验证
sudo ./diagnose_system.sh
```

### 问题 3: 服务启动失败

**症状**:
```
systemctl status airanking
Status: failed
```

**排查步骤**:

```bash
# 1. 查看详细日志
journalctl -u airanking -n 50

# 2. 查看服务器日志
tail -50 /var/www/airankingx.com/server.log

# 3. 检查文件是否存在
ls -l /var/www/airankingx.com/airankingx.py
```

**解决方案**:

```bash
# 1. 重新部署
sudo ./deploy.sh

# 2. 手动启动测试
cd /var/www/airankingx.com
sudo -u www-data python3 airankingx.py
# 观察输出
```

### 问题 4: 定时任务后网站出错

**症状**:
- 每小时网站短暂不可用
- 日志显示频繁重启

**解决方案**:

```bash
# 修改定时任务频率
sudo nano /etc/cron.d/airanking_monitor

# 改为每 12 小时一次:
0 */12 * * * root /bin/bash /var/www/airankingx.com/service_monitor.sh >> /var/www/airankingx.com/logs/monitor_cron.log 2>&1
```

---

## 工具脚本说明

### 核心脚本

#### `deploy.sh` - 完整部署

**用途**: 部署所有代码和配置到生产环境

**使用**:
```bash
sudo ./deploy.sh
```

**功能**:
- 创建备份
- 同步代码文件
- 部署 systemd 配置
- 设置权限
- 重启服务
- 验证权限
- 健康检查

#### `service_monitor.sh` - 服务监控

**用途**: 定时检查和修复服务状态

**使用**:
```bash
sudo ./service_monitor.sh
```

**功能**:
- 检查文件权限
- 检查服务状态
- 验证进程权限
- 检查 API 可访问性
- 自动修复问题

#### `restart_service_only.sh` - 快速重启

**用途**: 仅重启 Python 服务（不部署代码）

**使用**:
```bash
sudo ./restart_service_only.sh
```

### 诊断和修复脚本

#### `diagnose_system.sh` - 系统诊断

**用途**: 全面检查系统配置

**使用**:
```bash
sudo ./diagnose_system.sh
```

**检查项**:
- 用户和组配置
- 目录权限
- 文件权限
- 服务状态
- 进程权限
- systemd 配置
- Nginx 状态
- 端口监听
- 写入权限测试
- 定时任务配置
- 日志文件

#### `fix_permissions.sh` - 权限修复

**用途**: 一键修复所有权限问题

**使用**:
```bash
sudo ./fix_permissions.sh
```

**功能**:
- 确保 www-data 在 jerry 组中
- 设置父目录权限
- 设置代码库权限
- 设置生产环境权限
- 重启服务
- 验证权限
- 测试写入

#### `restart_python_server.sh` - 重启并验证

**用途**: 重启 Python 服务并验证权限

**使用**:
```bash
sudo ./restart_python_server.sh
```

**功能**:
- 停止旧进程
- 以 www-data 用户启动
- 验证组成员身份

### 日志工具

#### `view_logs.sh` - 日志查看

**用途**: 查看和过滤服务器日志

**使用**:
```bash
./view_logs.sh <模式> [-n 行数]
```

**模式**:
- `all` - 所有日志
- `success` - 成功操作
- `errors` - 错误
- `warnings` - 警告
- `updates` - 更新操作
- `sync` - 文件同步
- `stats` - 统计信息
- `live` - 实时监控
- `today` - 今天的日志

**示例**:
```bash
./view_logs.sh updates        # 查看更新操作
./view_logs.sh errors         # 查看错误
./view_logs.sh live           # 实时监控
./view_logs.sh all -n 100     # 查看最近 100 行
```

### 同步工具

#### `sync_csv_back.sh` - 手动同步

**用途**: 从生产环境同步 CSV 文件到代码库

**使用**:
```bash
sudo ./sync_csv_back.sh
```

#### `check_sync_status.sh` - 检查同步状态

**用途**: 检查两个目录的文件是否同步

**使用**:
```bash
./check_sync_status.sh
```

---

## 文件结构

```
/home/jerry/codebase/airanking/
├── README.md                          # 本文档 ⭐
├── airankingx.py                      # Python 服务器源码
├── app.js                             # 前端 JavaScript
├── index.html                         # 前端页面
├── styles.css                         # 样式文件
├── *.csv                              # CSV 数据文件
│
├── airanking.service                  # systemd 服务配置 ⭐
│
├── deploy.sh                          # 完整部署脚本 ⭐
├── service_monitor.sh                 # 服务监控脚本 ⭐
├── restart_service_only.sh            # 快速重启脚本
├── restart_python_server.sh           # 重启并验证脚本
├── fix_permissions.sh                 # 权限修复脚本 ⭐
├── diagnose_system.sh                 # 系统诊断脚本 ⭐
├── sync_csv_back.sh                   # 手动同步脚本
├── check_sync_status.sh               # 同步状态检查
├── view_logs.sh                       # 日志查看工具 ⭐
│
├── EXECUTE_NOW.md                     # 快速执行指南
├── COMPLETE_FIX_SUMMARY.md            # 完整修复总结
├── PERMISSION_FIX_GUIDE.md            # 权限修复指南
├── LOGGING_IMPROVEMENTS.md            # 日志改进说明
├── LOG_FORMAT.md                      # 日志格式详解
├── DEPLOYMENT_GUIDE.md                # 部署指南
├── QUICK_FIX.md                       # 快速修复指南
└── LOGGING_QUICKSTART.md              # 日志快速开始

/var/www/airankingx.com/               # 生产环境
├── airankingx.py                      # Python 服务器（运行中）
├── *.html, *.js, *.css                # 前端文件
├── *.csv                              # CSV 数据文件
├── server.log                         # 服务器日志
└── logs/                              # 监控日志目录

/etc/systemd/system/
└── airanking.service                  # systemd 服务配置

/etc/cron.d/
└── airanking_monitor                  # 定时任务配置
```

---

## 常见问题

### Q: 如何确认权限配置正确？

```bash
sudo ./diagnose_system.sh
# 应显示: ✓ 未发现严重问题！系统配置正常
```

### Q: 更新榜单后如何确认数据已同步？

```bash
# 检查同步状态
./check_sync_status.sh

# 或比较文件
diff /var/www/airankingx.com/team_building_record.csv \
     /home/jerry/codebase/airanking/team_building_record.csv
```

### Q: 如何查看实时日志？

```bash
./view_logs.sh live
```

### Q: 定时任务多久运行一次？

默认每小时运行一次。建议修改为每 12 小时：

```bash
sudo nano /etc/cron.d/airanking_monitor
# 改为: 0 */12 * * * root ...
```

### Q: 如何回滚到之前的版本？

```bash
# 查看可用备份
ls -lt /var/www/backups/airankingx.com/

# 恢复备份
sudo cp -r /var/www/backups/airankingx.com/20260109_HHMMSS/* \
           /var/www/airankingx.com/

# 重启服务
sudo systemctl restart airanking nginx
```

### Q: 如何禁用定时任务？

```bash
# 禁用定时任务
sudo rm /etc/cron.d/airanking_monitor

# 或注释掉
sudo nano /etc/cron.d/airanking_monitor
# 在行首添加 #
```

### Q: 网站密码是什么？

默认密码: `88888`

修改密码需要编辑两个文件：
```bash
# 1. 后端
nano /home/jerry/codebase/airanking/airankingx.py
# 修改: PassWord = "88888"

# 2. 前端
nano /home/jerry/codebase/airanking/app.js
# 修改: const PASSWORD = "88888";

# 3. 部署
sudo ./deploy.sh
```

---

## 维护检查清单

### 每日检查

- [ ] 查看日志统计: `./view_logs.sh stats`
- [ ] 检查最近的错误: `./view_logs.sh errors`
- [ ] 验证网站可访问

### 每周检查

- [ ] 运行系统诊断: `sudo ./diagnose_system.sh`
- [ ] 检查同步状态: `./check_sync_status.sh`
- [ ] 查看服务状态: `systemctl status airanking`
- [ ] 检查磁盘空间: `df -h`

### 每月维护

- [ ] 归档旧日志
- [ ] 备份 CSV 文件
- [ ] 清理旧备份
- [ ] 检查系统更新

---

## 紧急联系清单

### 服务完全宕机

```bash
# 1. 查看服务状态
systemctl status airanking
systemctl status nginx

# 2. 查看最近日志
journalctl -u airanking -n 100
tail -100 /var/www/airankingx.com/server.log

# 3. 尝试重启
sudo systemctl restart airanking nginx

# 4. 如果失败，重新部署
sudo ./deploy.sh
```

### 数据损坏

```bash
# 1. 停止服务
sudo systemctl stop airanking

# 2. 从备份恢复
sudo cp /var/www/airankingx.com/*.csv.bak /var/www/airankingx.com/

# 3. 或从代码库恢复
sudo cp /home/jerry/codebase/airanking/*.csv /var/www/airankingx.com/

# 4. 重启服务
sudo systemctl start airanking
```

### 权限完全错乱

```bash
# 运行完整修复
sudo ./fix_permissions.sh
sudo ./deploy.sh
sudo ./diagnose_system.sh
```

---

## 版本历史

### v2.0 (2026-01-09) - 权限问题完全解决

- ✅ 修复 systemd 服务配置（添加 SupplementaryGroups）
- ✅ 改进定时监控脚本（添加权限验证）
- ✅ 改进部署流程（自动验证权限）
- ✅ 新增权限修复脚本
- ✅ 新增系统诊断脚本
- ✅ 改进日志系统（11 步详细记录）
- ✅ 新增日志查看工具
- ✅ 完善文档

### v1.0 - 初始版本

- 基本的排行榜功能
- 游戏记录录入
- 玩家统计计算

---

## 支持和反馈

如果遇到问题：

1. 查看本文档相关章节
2. 运行 `sudo ./diagnose_system.sh` 诊断
3. 查看日志 `./view_logs.sh errors`
4. 收集诊断信息（见紧急联系清单）

---

## 许可证

内部使用项目

---

**最后更新**: 2026-01-09
**维护者**: jerry
**文档版本**: 2.0
