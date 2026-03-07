# CryptoSentinel Bot

基于 Telegram 的加密货币技术指标预警机器人。

## 功能特性

- **功能菜单**: `/start` 显示功能菜单，交互更友好
- **快捷交易对**: BTC/USDT、ETH/USDT 一键选择
- **多交易所支持**: OKX、Binance（理论上支持所有 ccxt 交易所）
- **多种时间周期**: 15m、1h、4h
- **技术指标监控**:
  - BB 布林带突破（影线触碰布林上轨）
  - VEGAS 触碰检测（K线影线触碰 EMA144/EMA169）
- **智能去重**: 基于 K 线时间戳，避免重复触发
- **币种验证**: 自动验证交易对是否支持，避免输入错误
- **命令自动补全**: 输入 `/` 自动显示命令列表
- **多语言支持**: 中文/英文切换，自动检测语言
- **VIP 会员系统**:
  - 普通用户：1 个监控指标
  - VIP 用户：5 个监控指标
  - 前 50 名注册用户免费赠送 14 天 VIP
- **管理员通知**: 充值申请自动通知管理员，带批准/拒绝按钮
- **异步架构**: 全链路 asyncio，单核性能最大化
- **进程解耦**: Bot/Engine/Notifier/VIPChecker 四进程独立运行

## 快速开始

### 1. 安装依赖

```bash
cd tg_vps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
nano .env
```

填入配置：
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_UID=your_telegram_uid
DEPOSIT_ADDRESS=your_trc20_wallet_address
```

### 3. 初始化数据库

```bash
python3 -c "import asyncio; from db_manager import init_db; asyncio.run(init_db())"
```

### 4. 启动服务

```bash
pm2 start run_bot.sh --name tg-bot
pm2 start run_engine.sh --name tg-engine
pm2 start run_notifier.sh --name tg-notifier
pm2 start run_vip.sh --name tg-vip
pm2 save
```

## Bot 命令

### 用户命令

| 命令 | 说明 |
|------|------|
| `/start` | 显示功能菜单 |
| `/list` | 查看当前监控列表 |
| `/delete [编号]` | 删除指定监控 |
| `/vip` | 查看 VIP 说明和充值 |
| `/deposit [交易哈希]` | 提交充值申请 |
| `/mystatus` | 查看我的 VIP 状态和监控列表 |
| `/myid` | 查看我的用户 ID |
| `/language` | 切换语言 |
| `/help` | 查看帮助 |

### 管理员命令

| 命令 | 说明 |
|------|------|
| `/admin` | 打开管理员控制面板 |
| `/setvip [UID] [天数]` | 手动开通 VIP |

### VIP 价格

- 价格：10 USDT/年（365天）
- 权益：5 个监控指标（普通用户 1 个）
- 支付方式：TRC20 USDT

## 项目结构

```
tg_vps/
├── bot.py              # Telegram Bot 前端
├── db_manager.py       # 数据库管理
├── market_engine.py    # 行情数据生产
├── notifier.py         # 信号监控与推送
├── vip_checker.py      # VIP 到期检测
├── run_engine_loop.py  # 行情引擎循环脚本
├── i18n.py             # 国际化工具
├── locales/            # 语言包
│   ├── zh.py           # 中文
│   └── en.py           # 英文
├── alphapulse.db       # SQLite 数据库
├── .env                # 环境变量配置
├── .env.example        # 环境变量示例
└── docs/               # 文档
    ├── ARCHITECTURE.md
    ├── DEPLOY_GUIDE.md
    └── DEVELOPER_MANUAL.md
```

## 技术栈

- **Python 3.10+**
- **python-telegram-bot v20+**
- **ccxt** - 交易所 API
- **pandas** - 数据计算
- **aiosqlite** - 异步 SQLite
- **PM2** - 进程管理

## 系统要求

- **CPU**: 1 核
- **内存**: 512MB+
- **存储**: 1GB+
- **系统**: Ubuntu 20.04+ / Debian 11+

## 文档

- [架构文档](docs/ARCHITECTURE.md)
- [部署指南](docs/DEPLOY_GUIDE.md)
- [开发手册](docs/DEVELOPER_MANUAL.md)

## License

MIT