# CryptoSentinel 运维与二次开发手册

> 面向初级开发者 | 1核1G VPS 环境 | 大白话 + 保姆级 Step-by-Step

---

## 目录

1. [服务器环境配置与启动部署](#1-服务器环境配置与启动部署)
2. [实战教学：如何添加一个新的交易所](#2-实战教学如何添加一个新的交易所)
3. [实战教学：如何添加一个新的监控策略](#3-实战教学如何添加一个新的监控策略)
4. [常见高频故障排除-faq](#4-常见高频故障排除-faq)
5. [命令功能速查](#5-命令功能速查)

---

## 1. 服务器环境配置与启动部署

### 1.1 安装 Python 3.10+ 环境

#### 步骤 1：更新系统包

```bash
# 登录 VPS 后，执行以下命令
sudo apt update && sudo apt upgrade -y
```

#### 步骤 2：安装 Python 3.11（推荐，比 3.10 更稳定）

```bash
# 安装 Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 设置为默认 Python
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# 验证安装
python3 --version
```

> ⚠️ 如果你用的是 Ubuntu 22.04+，系统自带 Python 3.10，可以跳过安装步骤。

#### 步骤 3：安装项目依赖

```bash
# 创建项目目录（如果你还没有）
mkdir -p ~/cryptosentinel && cd ~/cryptosentinel

# 创建虚拟环境（推荐，保护系统环境）
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装核心依赖
pip install aiosqlite ccxt pandas numpy python-telegram-bot
```

---

### 1.2 上传代码到服务器

#### 方法 A：使用 Git（推荐）

```bash
# 在服务器上
cd ~/cryptosentinel
git clone https://你的仓库地址 .

# 如果你已经有一份代码，只需要 git pull 更新
git pull
```

#### 方法 B：使用 SFTP 上传

1. 用 FileZilla 或 WinSCP 连接 VPS
2. 把本地文件夹 `tg_vps` 里的所有 `.py` 文件上传到服务器 `~/cryptosentinel/`

---

### 1.3 配置环境变量

```bash
cd ~/cryptosentinel

# 复制配置示例
cp .env.example .env

# 编辑配置文件
nano .env
```

在 `.env` 文件中填入你的 Bot Token：
```
TELEGRAM_BOT_TOKEN=你的Bot_Token
ADMIN_UID=你的Telegram_UID
DONATE_ADDRESS=你的TRC20钱包地址
```

---

### 1.4 初始化数据库

```bash
cd ~/cryptosentinel
source venv/bin/activate

# 初始化数据库（这步会自动创建 cryptosentinel.db）
python3 -c "import asyncio; from db_manager import init_db; asyncio.run(init_db())"
```

执行后，你应该会看到 `cryptosentinel.db` 文件被创建。

---

### 1.5 安装 PM2 并配置守护进程

#### 步骤 1：安装 Node.js（PM2 依赖）

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
node --version  # 确认安装成功
```

#### 步骤 2：安装 PM2

```bash
sudo npm install -g pm2
pm2 --version  # 确认安装成功
```

#### 步骤 3：创建行情引擎循环脚本

由于 `market_engine.py` 只执行一次就退出了，我们需要创建一个循环执行的脚本。

在 `~/cryptosentinel/` 目录下创建 `run_engine_loop.py`：

```python
#!/usr/bin/env python3
"""行情引擎定时执行器（每 60 秒执行一次）"""
import asyncio
import sys
import os

# 确保能导入同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    from market_engine import run_engine
    from db_manager import get_active_subs
    
    print("[Engine Loop] 行情引擎循环启动")
    
    while True:
        try:
            # 获取订阅
            subs = await get_active_subs()
            
            # 展平为简单列表
            flat_subs = []
            for key, items in subs.items():
                for item in items:
                    flat_subs.append({
                        "exchange": item["exchange"],
                        "symbol": item["symbol"],
                        "timeframe": item["timeframe"]
                    })
            
            if flat_subs:
                print(f"[Engine Loop] 执行 {len(flat_subs)} 个标的...")
                await run_engine(flat_subs)
            else:
                print("[Engine Loop] 暂无订阅")
                
        except Exception as e:
            print(f"[Engine Loop Error] {e}")
        
        await asyncio.sleep(60)  # 60 秒一轮

if __name__ == "__main__":
    asyncio.run(main())
```

#### 步骤 4：启动所有服务

```bash
cd ~/cryptosentinel
source venv/bin/activate

# 加载环境变量
export $(cat .env | xargs)

# 启动 Bot（前端）
pm2 start bot.py --name cryptosentinel-bot --interpreter python3

# 启动行情引擎（循环执行）
pm2 start run_engine_loop.py --name cryptosentinel-engine --interpreter python3

# 启动通知器（后台监控）
pm2 start notifier.py --name cryptosentinel-notifier --interpreter python3

# 查看状态
pm2 status

# 保存进程列表（开机自启）
pm2 save
```

#### 步骤 5：常用 PM2 命令

```bash
# 查看日志
pm2 logs

# 只看 bot 日志
pm2 logs cryptosentinel-bot

# 重启某个模块
pm2 restart cryptosentinel-bot

# 查看实时日志（类似 tail -f）
pm2 logs --lines 100 --nostream

# 停止所有
pm2 stop all

# 删除所有进程
pm2 delete all

# 设置开机自启
pm2 save
sudo env PATH=$PATH:/usr/bin /usr/lib/node_modules/pm2/bin/pm2 startup systemd -u $USER --hp $HOME
```

---

## 2. 实战教学：如何添加一个新的交易所

> 以添加 **币安 (Binance)** 为例，其实现在代码已经支持了，但让我演示修改流程

### 2.1 前端同步修改：Bot 按钮

打开 `bot.py`，找到交易所选择的键盘配置：

```python
# 找到这段代码
keyboard = [
    [
        InlineKeyboardButton("Binance", callback_data="Binance"),
        InlineKeyboardButton("OKX", callback_data="OKX"),
    ]
]
reply_markup = InlineKeyboardMarkup(keyboard)
```

**要添加新交易所（比如 Bybit）**，只需要加一行：

```python
keyboard = [
    [
        InlineKeyboardButton("Binance", callback_data="Binance"),
        InlineKeyboardButton("OKX", callback_data="OKX"),
        InlineKeyboardButton("Bybit", callback_data="Bybit"),  # 新增这行
    ]
]
```

> 💡 **关键点**：`callback_data` 的值就是后面会收到的交易所标识，必须和 ccxt 支持的名称一致（小写）。

### 2.2 后端配置修改：ccxt 初始化

好消息是：**你几乎不需要改任何代码！**

因为 `market_engine.py` 已经用了通用方式获取交易所实例：

```python
# market_engine.py
exchange_class = getattr(ccxt, exchange_name.lower())  # 自动根据名称获取
exchange = exchange_class({
    "enableRateLimit": True,
    "timeout": REQUEST_TIMEOUT * 1000,
})
```

所以只要 `callback_data` 填的是 ccxt 支持的交易所名称（全部小写），代码就能自动适配。

**如果你想验证支持的交易所列表**，可以在 Python 里运行：

```python
import ccxt
print(ccxt.exchanges)  # 打印所有支持的交易所
```

---

## 3. 实战教学：如何添加一个新的监控策略

> 以添加 **MACD 金叉** 为例

### 3.1 数据生产：在 market_engine.py 中计算 MACD

打开 `market_engine.py`，找到 `calculate_ema` 和 `calculate_bbands` 函数的位置。

在它们后面添加 MACD 计算函数：

```python
# 在 market_engine.py 中添加

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    计算 MACD 指标
    
    Args:
        series: 价格序列
        fast: 快线周期
        slow: 慢线周期  
        signal: 信号线周期
    
    Returns:
        包含 macd, signal, histogram 的字典
    """
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    
    return {"macd": macd, "signal": signal_line, "histogram": histogram}
```

然后在 `fetch_and_calc` 函数里调用它：

```python
# 在 fetch_and_calc 函数里添加
macd_result = calculate_macd(close_series)
df["MACD_12_26_9"] = macd_result["macd"]
df["MACD_signal"] = macd_result["signal"]
df["MACD_hist"] = macd_result["histogram"]
```

最后在提取结果的字典里添加字段：

```python
result = {
    # ... 原有字段 ...
    "MACD_12_26_9": float(latest["MACD_12_26_9"]) if pd.notna(latest.get("MACD_12_26_9")) else None,
    "MACD_signal": float(latest["MACD_signal"]) if pd.notna(latest.get("MACD_signal")) else None,
    "MACD_hist": float(latest["MACD_hist"]) if pd.notna(latest.get("MACD_hist")) else None,
}
```

### 3.2 信号比对：在 notifier.py 中添加判定逻辑

打开 `notifier.py`，添加 MACD 信号检查函数：

```python
# 在 notifier.py 中添加

def check_macd_cross_signal(market_data: Dict[str, Any], sub: Dict[str, Any]) -> bool:
    """
    检查 MACD 金叉信号
    
    逻辑：MACD 线从下方穿过信号线 -> 金叉（多头信号）
    """
    macd = market_data.get("MACD_12_26_9")
    signal = market_data.get("MACD_signal")
    
    if macd is None or signal is None:
        return False
    
    # 金叉：MACD > Signal 且 前一根 MACD <= Signal
    # 这里简化为只判断当前状态
    return macd > signal
```

然后找到 `check_signal` 函数，添加 MACD 分支：

```python
# 在 check_signal 函数里添加新分支

def check_signal(market_data: Dict[str, Any], sub: Dict[str, Any]) -> Optional[str]:
    indicator = sub.get("indicator", "").upper()
    
    if indicator == "BB":
        # ... 原有的 BB 逻辑 ...
        pass
    
    elif indicator == "VEGAS":
        # ... 原有的 VEGAS 逻辑 ...
        pass
    
    elif indicator == "MACD":  # 新增 MACD 分支
        if not check_macd_cross_signal(market_data, sub):
            return None
        
        symbol = market_data.get("symbol")
        macd = market_data.get("MACD_12_26_9")
        signal = market_data.get("MACD_signal")
        
        if macd is None or signal is None:
            return None
        
        msg = f"📊 MACD 金叉信号\n{symbol} MACD({macd:.4f}) 上穿信号线({signal:.4f})"
        return msg
    
    return None
```

### 3.3 前端同步：Bot 添加按钮

打开 `bot.py`，找到指标选择键盘：

```python
# 找到这段代码
keyboard = [
    [
        InlineKeyboardButton("BB 布林带", callback_data="BB"),
        InlineKeyboardButton("VEGAS 通道", callback_data="VEGAS"),
    ]
]
reply_markup = InlineKeyboardMarkup(keyboard)
```

修改为：

```python
keyboard = [
    [
        InlineKeyboardButton("BB 布林带", callback_data="BB"),
        InlineKeyboardButton("VEGAS 通道", callback_data="VEGAS"),
        InlineKeyboardButton("MACD 金叉", callback_data="MACD"),  # 新增
    ]
]
reply_markup = InlineKeyboardMarkup(keyboard)
```

同时修改 `confirm_callback` 里的参数构建：

```python
if indicator == "BB":
    params = {"period": 20, "std_dev": 2}
elif indicator == "VEGAS":
    params = {"ema_fast": 144, "ema_slow": 169}
elif indicator == "MACD":  # 新增
    params = {"fast": 12, "slow": 26, "signal": 9}
```

---

## 4. 常见高频故障排除 (FAQ)

### 故障 1：机器人没反应

#### 可能原因 1：Bot 进程挂了

```bash
# 查看进程状态
pm2 status

# 如果看到 stopped 或 error，重启
pm2 restart cryptosentinel-bot

# 查看具体报错
pm2 logs cryptosentinel-bot --lines 50
```

#### 可能原因 2：Bot Token 填错了

检查 `.env` 文件中的 `TELEGRAM_BOT_TOKEN` 是否正确。

#### 可能原因 3：数据库被锁住

```bash
# 删除锁文件（如果有）
rm -f cryptosentinel.db-journal

# 重启所有服务
pm2 restart all
```

---

### 故障 2：日志提示网络超时

#### 原因分析

这通常是因为：
1. VPS 网络不好（特别是国内 VPS 访问国外交易所）
2. 交易所限流
3. 请求超时

#### 解决步骤

**步骤 1：查看是哪个标的超时**

```bash
pm2 logs cryptosentinel-engine
```

找到类似这样的日志：
```
[超时] okx BTC/USDT 15m: RequestTimeout
```

**步骤 2：检查网络**

```bash
# 测试到交易所的连接
ping okx.com
curl -I https://www.okx.com
```

**步骤 3：增加超时时间**

打开 `market_engine.py`：

```python
REQUEST_TIMEOUT = 10  # 改成 20 或 30
```

**步骤 4：增加重试次数和休眠时间**

```python
MAX_RETRIES = 3        # 改成 5
BASE_SLEEP = 1        # 改成 2
```

改完后重启：

```bash
pm2 restart cryptosentinel-engine
```

---

### 故障 3：SQLite 锁死

#### 原因分析

多个进程同时读写数据库，导致 SQLite 锁死。

#### 解决步骤

**步骤 1：检查数据库文件状态**

```bash
ls -la cryptosentinel.db*
```

如果看到 `cryptosentinel.db-journal`，说明有未完成的操作。

**步骤 2：删除锁文件**

```bash
rm -f cryptosentinel.db-journal
rm -f cryptosentinel.db-wal
rm -f cryptosentinel.db-shm
```

**步骤 3：重启所有服务**

```bash
pm2 restart all
```

---

### 故障 4：内存不足 (OOM)

#### 症状

VPS 开始变卡，日志里看到 Python 被杀掉：

```
Killed
```

#### 解决步骤

**步骤 1：检查内存使用**

```bash
free -h
pm2 monit
```

**步骤 2：减少 DataFrame 大小**

打开 `market_engine.py`：

```python
limit=200  # 改成 100，减少内存占用
```

**步骤 3：定期重启**

添加定时重启配置：

```javascript
module.exports = {
  apps: [
    {
      name: 'cryptosentinel-engine',
      script: 'engine_runner.py',
      interpreter: 'python3',
      max_memory_restart: '300M',  // 超过 300MB 自动重启
      cron_restart: '0 6 * * *',  // 每天凌晨 6 点重启
    }
  ]
}
```

---

## 5. 命令功能速查

### 5.1 用户命令一览

| 命令 | 用法示例 | 功能说明 |
|------|----------|----------|
| `/start` | `/start` | 显示功能菜单 |
| `/list` | `/list` | 查看当前用户所有监控任务 |
| `/delete` | `/delete 123` | 删除编号为 123 的监控任务 |
| `/donate` | `/donate` | 显示打赏地址 |
| `/myid` | `/myid` | 查看我的用户 ID |
| `/help` | `/help` | 查看所有可用命令 |
| `/cancel` | `/cancel` | 取消当前进行中的对话 |

### 5.2 管理员命令一览

| 命令 | 用法示例 | 功能说明 |
|------|----------|----------|
| `/admin` | `/admin` | 打开管理员控制面板（按钮交互） |

### 5.3 /list 命令示例

```
用户发送: /list

Bot 回复:
📋 您的监控任务列表：

✅ #1 OKX BTC/USDT
   周期: 15m | 指标: BB

✅ #2 Binance ETH/USDT
   周期: 1h | 指标: VEGAS

💡 使用 /delete [编号] 删除任务
```

### 5.4 /delete 命令示例

```
用户发送: /delete 1

Bot 回复: ✅ 已删除监控任务 #1
```

---

## 6. 前端文字调整指南

### 6.1 文字存储位置

所有用户可见的文字存储在语言包中：

```
locales/
├── zh.py    # 中文语言包
└── en.py    # 英文语言包
```

### 6.2 修改提示文字

**示例：修改打赏说明**

```python
# locales/zh.py
MESSAGES = {
    "donate_content": "感谢您使用 CryptoSentinel！\n\n如果这个项目对您有帮助，欢迎打赏支持开发者 ❤️\n\n📍 打赏地址 (TRC20)：\n<code>{address}</code>",
    ...
}
```

修改后重启 Bot：
```bash
pm2 restart cryptosentinel-bot
```

### 6.3 修改按钮文字

```python
# locales/zh.py
MESSAGES = {
    "btn_confirm": "✅ 确认",
    "btn_cancel": "❌ 取消",
    ...
}
```

### 6.4 添加新的文字

1. 在 `locales/zh.py` 和 `locales/en.py` 中添加：
```python
MESSAGES = {
    "new_message_key": "新的提示文字",
    ...
}
```

2. 在代码中使用：
```python
lang = await get_lang(update)
text = get_message("new_message_key", lang)
```

### 6.5 带参数的文字

```python
# 语言包
MESSAGES = {
    "max_subs_reached": "❌ 您已达到订阅上限 ({max} 个)。",
}

# 代码中使用
text = get_message("max_subs_reached", lang, max=10)
```

---

## 7. 多语言系统

### 7.1 支持的语言

| 语言 | 代码 | 文件 |
|------|------|------|
| 中文 | `zh` | `locales/zh.py` |
| 英文 | `en` | `locales/en.py` |

### 7.2 语言检测机制

```
用户首次使用
    ↓
检查数据库是否有语言设置
    ↓
无 → 使用 Telegram language_code 自动检测
    ↓
用户可随时通过 /language 切换
    ↓
保存到数据库 users.language 字段
```

### 7.3 切换语言命令

```
用户发送: /language

Bot 回复:
🌐 选择语言 / Select language:

[🇨🇳 中文]
[🇺🇸 English]
```

### 7.4 添加新语言

1. 创建语言包 `locales/xx.py`
2. 在 `i18n.py` 中注册：
```python
from locales.xx import MESSAGES as XX_MESSAGES

LANGUAGES = {
    "zh": ZH_MESSAGES,
    "en": EN_MESSAGES,
    "xx": XX_MESSAGES,  # 新增
}
```

3. 在语言选择按钮中添加

---

## 附录：快速命令速查表

```bash
# 激活环境
cd ~/cryptosentinel && source venv/bin/activate

# 加载环境变量
export $(cat .env | xargs)

# 查看日志
pm2 logs

# 重启所有
pm2 restart all

# 停止所有
pm2 stop all

# 查看状态
pm2 status

# 开机自启设置
pm2 save && sudo pm2 startup
```

---

*文档版本：v3.0*  
*最后更新：2026-04-08*