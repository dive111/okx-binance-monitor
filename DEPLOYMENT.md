# OKX/Binance 公告监控系统 - Ubuntu 服务器部署指南

本指南将帮助你在 Ubuntu 服务器上部署公告监控系统，实现 7x24 小时自动运行。

---

## 📋 部署前准备

### 需要的信息
1. **Telegram Bot Token**（从 @BotFather 获取）
2. **Telegram 群组 Chat ID**（从 @getidsbot 获取）
3. **服务器 SSH 访问权限**

---

## 🚀 部署步骤

### 第一步：连接到服务器

通过 SSH 连接到你的 Ubuntu 服务器：

```bash
ssh username@your_server_ip
```

替换 `username` 为你的用户名，`your_server_ip` 为服务器IP地址。

---

### 第二步：检查 Python 版本

确保服务器上有 Python 3.7 或更高版本：

```bash
python3 --version
```

如果显示类似 `Python 3.8.10` 或更高版本，就可以继续。

如果没有安装 Python，运行：

```bash
sudo apt update
sudo apt install python3 python3-pip -y
```

---

### 第三步：克隆代码仓库

在你的服务器上选择一个目录，然后克隆代码：

```bash
# 创建项目目录
mkdir -p ~/okx-binance-monitor
cd ~/okx-binance-monitor

# 克隆代码（替换为你的Git仓库地址）
git clone <你的Git仓库地址> .
```

**注意**：如果你还没有把代码推送到远程仓库，可以先在本地推送到 GitHub/GitLab，或者使用 SCP/SFTP 直接上传文件。

---

### 第四步：配置环境变量

创建 `.env` 文件并填入你的配置：

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件
nano .env
```

在编辑器中，修改以下两行：

```bash
TELEGRAM_BOT_TOKEN=你的实际Bot_Token
TELEGRAM_CHAT_ID=你的实际Chat_ID
```

保存文件：
- 按 `Ctrl + O` 保存
- 按 `Enter` 确认
- 按 `Ctrl + X` 退出

---

### 第五步：安装 Python 依赖包

```bash
# 安装依赖
pip3 install -r requirements.txt
```

如果提示权限问题，可以加上 `--user` 参数：

```bash
pip3 install --user -r requirements.txt
```

---

### 第六步：测试运行

先手动运行一次，确保程序正常工作：

```bash
python3 monitor.py
```

你应该看到类似的输出：

```
2026-07-05 12:00:00,000 - INFO - ==================================================
2026-07-05 12:00:00,000 - INFO - OKX/Binance 公告监控系统启动
2026-07-05 12:00:00,000 - INFO - 检查间隔: 10 分钟
2026-07-05 12:00:00,000 - INFO - Telegram Chat ID: -5435135504
2026-07-05 12:00:00,000 - INFO - 首次运行，只监控新公告（不发送历史公告）
2026-07-05 12:00:00,000 - INFO - ==================================================
2026-07-05 12:00:00,000 - INFO - 初始化：加载现有公告ID...
```

**测试成功标志**：
- ✅ 没有报错
- ✅ 能看到 "初始化完成，开始监控..."
- ✅ Telegram 群组收到测试消息（如果有新公告）

按 `Ctrl + C` 停止程序。

---

### 第七步：配置 systemd 服务（7x24小时运行）

为了让程序在后台持续运行，并且开机自动启动，需要创建 systemd 服务。

#### 1. 创建服务文件

```bash
sudo nano /etc/systemd/system/okx-binance-monitor.service
```

#### 2. 粘贴以下内容

**重要**：修改下面的路径和用户名为你自己的！

```ini
[Unit]
Description=OKX/Binance Announcement Monitor
After=network.target

[Service]
Type=simple
User=你的用户名
WorkingDirectory=/home/你的用户名/okx-binance-monitor
EnvironmentFile=/home/你的用户名/okx-binance-monitor/.env
ExecStart=/usr/bin/python3 /home/你的用户名/okx-binance-monitor/monitor.py
Restart=always
RestartSec=10
StandardOutput=append:/home/你的用户名/okx-binance-monitor/monitor.log
StandardError=append:/home/你的用户名/okx-binance-monitor/monitor-error.log

[Install]
WantedBy=multi-user.target
```

**修改说明**：
- 把所有 `你的用户名` 替换为你的实际用户名（可以用 `whoami` 命令查看）
- 如果 Python 路径不同，用 `which python3` 查看正确路径

保存并退出（`Ctrl+O`, `Enter`, `Ctrl+X`）。

#### 3. 重新加载 systemd

```bash
sudo systemctl daemon-reload
```

#### 4. 启动服务

```bash
sudo systemctl start okx-binance-monitor
```

#### 5. 设置开机自启

```bash
sudo systemctl enable okx-binance-monitor
```

#### 6. 检查服务状态

```bash
sudo systemctl status okx-binance-monitor
```

应该看到 `active (running)` 状态。

---

### 第八步：查看日志

#### 实时查看日志

```bash
# 查看程序输出日志
tail -f ~/okx-binance-monitor/monitor.log

# 或者使用 journalctl
sudo journalctl -u okx-binance-monitor -f
```

按 `Ctrl + C` 退出日志查看。

#### 查看最近的日志

```bash
# 查看最后50行
tail -n 50 ~/okx-binance-monitor/monitor.log
```

---

## 🔧 常用管理命令

### 启动服务
```bash
sudo systemctl start okx-binance-monitor
```

### 停止服务
```bash
sudo systemctl stop okx-binance-monitor
```

### 重启服务
```bash
sudo systemctl restart okx-binance-monitor
```

### 查看服务状态
```bash
sudo systemctl status okx-binance-monitor
```

### 查看日志
```bash
sudo journalctl -u okx-binance-monitor -n 100
```

### 禁用开机自启
```bash
sudo systemctl disable okx-binance-monitor
```

---

## ⚠️ 故障排查

### 问题1：服务启动失败

查看错误日志：

```bash
sudo journalctl -u okx-binance-monitor -n 50 --no-pager
```

常见原因：
- **环境变量未设置**：检查 `.env` 文件是否存在且格式正确
- **Python 路径错误**：用 `which python3` 确认路径
- **权限问题**：确保用户有读取文件的权限

### 问题2：收不到 Telegram 消息

检查：
1. Bot 是否在群组中且有发送权限
2. Chat ID 是否正确（应该是负数，如 `-5435135504`）
3. 查看日志是否有发送失败的错误

### 问题3：程序崩溃

查看错误日志：

```bash
cat ~/okx-binance-monitor/monitor-error.log
```

---

## 📝 更新代码

当代码有更新时：

```bash
cd ~/okx-binance-monitor

# 拉取最新代码
git pull

# 重启服务
sudo systemctl restart okx-binance-monitor
```

---

## 🔒 安全建议

1. **不要公开 `.env` 文件**：它包含你的 Bot Token
2. **定期备份数据**：备份 `sent_announcements.json` 文件
3. **监控磁盘空间**：日志文件可能会增长，定期清理

清理旧日志：

```bash
# 保留最近7天的日志
find ~/okx-binance-monitor -name "*.log" -mtime +7 -delete
```

---

## ✅ 部署完成检查清单

- [ ] Python 3.7+ 已安装
- [ ] 代码已克隆到服务器
- [ ] `.env` 文件已配置（包含 Bot Token 和 Chat ID）
- [ ] 依赖包已安装（`pip3 install -r requirements.txt`）
- [ ] 手动测试运行成功
- [ ] systemd 服务已创建
- [ ] 服务正在运行（`systemctl status` 显示 active）
- [ ] 开机自启已启用（`systemctl is-enabled` 显示 enabled）
- [ ] Telegram 群组能收到消息
- [ ] 日志正常记录

---

## 📞 需要帮助？

如果遇到问题，可以：
1. 查看日志文件：`~/okx-binance-monitor/monitor.log`
2. 检查服务状态：`sudo systemctl status okx-binance-monitor`
3. 查看详细错误：`sudo journalctl -u okx-binance-monitor -n 100`

祝部署顺利！🎉
