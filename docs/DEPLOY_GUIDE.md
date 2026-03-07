# CryptoSentinel 部署指南

> 从零开始，包含 VPS 准备、Telegram Bot 申请、完整部署流程

---

## 目录

1. [VPS 环境准备](#1-vps-环境准备)
2. [申请 Telegram Bot](#2-申请-telegram-bot)
3. [项目部署](#3-项目部署)
4. [验证与测试](#4-验证与测试)
5. [常见问题](#5-常见问题)

---

## 1. VPS 环境准备

### 1.1 系统要求

| 项目 | 最低要求 |
|------|----------|
| CPU | 1 核 |
| 内存 | 512MB |
| 存储 | 1GB |
| 系统 | Ubuntu 20.04+ / Debian 11+ |

### 1.2 安装 Python 3.11

```bash
# 更新系统
sudo apt update

# 安装 Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# 设置为默认 Python3
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# 验证
python3 --version
```

### 1.3 安装 Node.js 和 PM2

```bash
# 安装 Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# 安装 PM2
sudo npm install -g pm2

# 设置开机自启
pm2 startup
```

---

## 2. 申请 Telegram Bot

### 2.1 创建 Bot

1. 在 Telegram 搜索 `@BotFather`
2. 发送 `/newbot`
3. 按提示设置 Bot 名称和用户名
4. 记录返回的 **Token**（格式：`1234567890:ABCdef...`）

### 2.2 获取管理员 UID

1. 在 Telegram 搜索 `@userinfobot`
2. 发送任意消息
3. 记录返回的 **ID**（格式：`123456789`）

---

## 3. 项目部署

### 3.1 上传代码

**方式 A：Git 克隆（推荐）**

```bash
cd ~
git clone https://你的仓库地址 cryptosentinel
cd cryptosentinel
```

**方式 B：SFTP 上传**

使用 FileZilla 或 WinSCP 上传代码到 `~/cryptosentinel/`

### 3.2 安装依赖

```bash
cd ~/cryptosentinel

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3.3 配置环境变量

```bash
cd ~/cryptosentinel

# 复制配置示例
cp .env.example .env

# 编辑配置
nano .env
```

**填入以下内容：**

```bash
# Telegram Bot Token（从 @BotFather 获取）
TELEGRAM_BOT_TOKEN=你的Bot_Token

# 管理员 UID（从 @userinfobot 获取）
ADMIN_UID=你的Telegram_UID

# VIP 充值地址（TRC20）
DEPOSIT_ADDRESS=你的TRC20钱包地址
```

### 3.4 初始化数据库

```bash
cd ~/cryptosentinel
source venv/bin/activate

# 初始化数据库
python3 -c "import asyncio; from db_manager import init_db; asyncio.run(init_db())"

# 验证
ls -la cryptosentinel.db
```

### 3.4 创建启动脚本

创建 `run_bot.sh`：

```bash
#!/bin/bash
cd ~/cryptosentinel
source venv/bin/activate
export $(cat .env | xargs)
python3 bot.py
```

创建 `run_engine.sh`：

```bash
#!/bin/bash
cd ~/cryptosentinel
source venv/bin/activate
python3 run_engine_loop.py
```

创建 `run_notifier.sh`：

```bash
#!/bin/bash
cd ~/cryptosentinel
source venv/bin/activate
export $(cat .env | xargs)
python3 notifier.py
```

创建 `run_vip.sh`：

```bash
#!/bin/bash
cd ~/cryptosentinel
source venv/bin/activate
export $(cat .env | xargs)
python3 vip_checker.py
```

赋予执行权限：

```bash
chmod +x run_*.sh
```

### 3.8 启动所有服务

```bash
cd ~/cryptosentinel

# 启动 Bot（前端交互）
pm2 start run_bot.sh --name cryptosentinel-bot

# 启动行情引擎
pm2 start run_engine.sh --name cryptosentinel-engine

# 启动通知器
pm2 start run_notifier.sh --name cryptosentinel-notifier

# 启动 VIP 检查器
pm2 start run_vip.sh --name cryptosentinel-vip

# 保存进程列表
pm2 save
```

---

## 4. 验证与测试

### 4.1 检查进程状态

```bash
pm2 status
```

**预期输出：**

```
┌─────┬──────────────────────┬──────────┬──────┬───────┬──────────┐
│ Name                 │ Mode     │ ↺    │ Status│ CPU      │ Memory   │
├─────┼──────────────────────┼──────────┼──────┼───────┼──────────┤
│ cryptosentinel-bot       │ fork     │ 0    │ online│ 0.0%    │ 120MB    │
│ cryptosentinel-engine   │ fork     │ 0    │ online│ 0.0%    │ 95MB     │
│ cryptosentinel-notifier │ fork     │ 0    │ online│ 0.0%    │ 80MB     │
│ cryptosentinel-vip      │ fork     │ 0    │ online│ 0.0%    │ 30MB     │
└─────┴──────────────────────┴──────────┴──────┴───────┴──────────┘
```

### 4.2 测试用户命令

在 Telegram 中向你的 Bot 发送：

| 命令 | 预期结果 |
|------|----------|
| `/start` | 显示交易所选择按钮 |
| `/language` | 显示语言选择按钮 |
| `/vip` | 显示 VIP 说明和充值地址 |
| `/myid` | 显示你的 UID |
| `/help` | 显示命令列表 |

### 4.3 测试订阅流程

```
发送 /start
    ↓
选择交易所（OKX 或 Binance）
    ↓
输入交易对（如 BTC/USDT）
    ↓
选择时间周期（15m/1h/4h）
    ↓
选择指标（BB 或 VEGAS）
    ↓
确认保存
    ↓
发送 /list 查看订阅
```

### 4.4 测试币种验证

```
发送 /start
    ↓
选择交易所
    ↓
输入不存在的币种（如 ABC/USDT）
    ↓
应显示"该交易对不被支持"并列出热门币种
```

### 4.5 测试 VIP 功能（管理员）

```
发送 /admin
    ↓
应显示管理员面板
    ↓
点击"充值申请列表"
    ↓
应显示待处理列表（暂无）
```

### 4.6 查看日志

```bash
# 查看所有日志
pm2 logs

# 只看 Bot 日志
pm2 logs cryptosentinel-bot

# 只看最近 50 行
pm2 logs --lines 50

# 实时监控
pm2 monit
```

---

## 5. 常见问题

### Q1：Bot 没有任何反应

```bash
# 检查进程状态
pm2 status

# 如果不是 online，重启
pm2 restart cryptosentinel-bot

# 查看错误日志
pm2 logs cryptosentinel-bot --lines 30

# 检查 Token 是否正确
cat .env
```

### Q2：提示网络超时

```bash
# 测试网络连接
ping google.com

# 测试 OKX API
curl -I https://www.okx.com

# 如果是国内 VPS，可能需要代理
```

### Q3：数据库锁定错误

```bash
# 检查数据库文件
ls -la cryptosentinel.db*

# 删除锁文件
rm -f cryptosentinel.db-wal cryptosentinel.db-shm

# 重启所有服务
pm2 restart all
```

### Q4：VIP 充值后没有开通？

```bash
# 检查充值申请列表（管理员）
# 发送 /admin → 点击"充值申请列表"

# 手动开通 VIP（管理员）
/setvip 用户UID 天数

# 示例：为用户 123456789 开通 365 天 VIP
/setvip 123456789 365
```

### Q5：如何修改 VIP 价格？

编辑 `db_manager.py`：

```python
VIP_PRICE_USDT = 10        # VIP 价格
VIP_DURATION_DAYS = 365    # VIP 时长（天）
```

修改后重启：

```bash
pm2 restart cryptosentinel-bot
```

### Q6：如何修改提醒格式？

**BB 信号**：编辑 `notifier.py` 第 222 行

```python
return f"🚀 BB 突破信号\n{symbol} 收盘价 {close:.2f} 突破布林上轨 {bbu:.2f}"
```

**VEGAS 信号**：编辑 `notifier.py` 第 244-249 行

```python
if signal_type == "cross_up_144":
    msg_parts.append(f"⬆️ {symbol} K线上穿 EMA144 ({ema_144:.2f})")
```

### Q7：如何更新代码？

```bash
cd ~/cryptosentinel

# Git 更新
git pull

# 重启服务
pm2 restart all
```

### Q8：如何备份数据？

```bash
# 备份数据库
cp cryptosentinel.db cryptosentinel.db.backup

# 备份到本地
scp user@vps_ip:~/cryptosentinel/cryptosentinel.db ./
```

### Q9：内存占用过高？

```bash
# 查看内存占用
pm2 monit

# 定期重启（每天凌晨 6 点）
pm2 start cryptosentinel-bot --cron-restart="0 6 * * *"
```

### Q10：如何查看支持哪些币种？

Bot 会自动从 OKX API 获取支持的交易对列表。

用户输入不支持的币种时，会显示热门币种列表：
- BTC/USDT
- ETH/USDT
- SOL/USDT
- XRP/USDT
- DOGE/USDT
- ADA/USDT
- AVAX/USDT
- DOT/USDT
- MATIC/USDT
- LINK/USDT

---

## 快速命令速查表

```bash
# 激活环境
cd ~/cryptosentinel && source venv/bin/activate

# 加载环境变量
export $(cat .env | xargs)

# 查看状态
pm2 status

# 查看日志
pm2 logs

# 重启所有
pm2 restart all

# 重启单个
pm2 restart cryptosentinel-bot

# 停止所有
pm2 stop all

# 开机自启
pm2 save && pm2 startup
```

---

## 项目结构

```
cryptosentinel/
├── bot.py                   # Telegram Bot 前端
├── db_manager.py            # 数据库管理
├── market_engine.py         # 行情数据生产
├── notifier.py              # 信号监控与推送
├── vip_checker.py           # VIP 到期检测
├── run_engine_loop.py       # 行情引擎循环脚本
├── i18n.py                  # 国际化工具
├── locales/                 # 语言包
│   ├── zh.py                # 中文
│   └── en.py                # 英文
├── cryptosentinel.db        # SQLite 数据库
├── cryptosentinel_cache.json # 行情缓存
├── .env                     # 环境变量配置
├── .env.example             # 环境变量示例
└── docs/                    # 文档
    ├── ARCHITECTURE.md
    ├── DEVELOPER_MANUAL.md
    └── I18N_GUIDE.md
```

---

*文档版本：v1.5*  
*最后更新：2025-03-07*