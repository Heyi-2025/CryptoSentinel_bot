# CryptoSentinel 加密货币预警机器人 - 架构文档

## 1. 系统解耦架构概述

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CryptoSentinel 系统架构                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   bot.py     │  │market_engine │  │  notifier.py │                  │
│  │  (前端交互)   │  │  (行情生产)   │  │  (信号消费)   │                  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                  │
│         │                 │                 │                           │
│         ▼                 ▼                 ▼                           │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │                    SQLite (cryptosentinel.db)                │       │
│  │                 用户数据 + 订阅配置 + 语言设置                  │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                              ▲                                          │
│                              │                                          │
│                        ┌─────┴─────┐                                    │
│                        │cryptosentinel│                                 │
│                        │  _cache.json │                                 │
│                        └────────────┘                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 模块职责与通信机制

| 模块 | 职责 | 数据出口 | 通信方式 |
|------|------|----------|----------|
| **bot.py** | Telegram 前端交互，订阅管理，打赏展示 | 写入 `subscriptions` 表 | 直接调用 `db_manager` |
| **market_engine.py** | 轮询交易所，抓取 K 线，计算指标 | 写入 `cryptosentinel_cache.json` | 读取 `subscriptions` 表 |
| **notifier.py** | 监控缓存变化，比对信号，推送消息 | 消费 `message_queue` | 读取 `subscriptions` + `cryptosentinel_cache.json` |

### 1.3 核心设计原则

- **前后端物理解耦**：Bot/Engine/Notifier 三进程独立运行，通过 SQLite 和 JSON 缓存异步通信，互不阻塞。
- **纯异步架构**：全链路使用 `asyncio`，确保单核性能最大化。
- **内存安全**：K 线数据随用随弃，只保留最新一根 K 线的指标结果。

---

## 2. 核心数据库字典

### 2.1 数据库文件

```
cryptosentinel.db
```

### 2.2 表结构

#### 2.2.1 users 表

| 字段名 | 数据类型 | 主键 | 默认值 | 说明 |
|--------|----------|------|--------|------|
| `uid` | INTEGER | ✅ | - | Telegram 用户 ID |
| `language` | TEXT | - | 'zh' | 用户语言偏好 |
| `created_at` | TIMESTAMP | - | CURRENT_TIMESTAMP | 注册时间 |

```sql
CREATE TABLE users (
    uid INTEGER PRIMARY KEY,
    language TEXT DEFAULT 'zh',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.2.2 subscriptions 表

| 字段名 | 数据类型 | 主键/外键 | 默认值 | 说明 |
|--------|----------|-----------|--------|------|
| `sub_id` | INTEGER | 主键 (自增) | - | 订阅记录唯一 ID |
| `uid` | INTEGER | 外键 → users.uid | - | 所属用户 ID |
| `exchange` | TEXT | - | - | 交易所名称 (OKX/Binance) |
| `symbol` | TEXT | - | - | 交易对 (BTC/USDT) |
| `timeframe` | TEXT | - | - | K 线周期 (15m/1h/4h) |
| `indicator` | TEXT | - | - | 技术指标 (BB/VEGAS) |
| `params` | TEXT | - | - | 指标参数 JSON 字符串 |
| `is_active` | BOOLEAN | - | 1 | 是否激活 (1=激活) |

```sql
CREATE TABLE subscriptions (
    sub_id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid INTEGER,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    indicator TEXT NOT NULL,
    params TEXT,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (uid) REFERENCES users(uid)
);
```

---

## 3. 管理员系统

### 3.1 管理员权限

管理员 UID 通过环境变量配置（`bot.py`）：
```python
ADMIN_UID = int(os.environ.get("ADMIN_UID", "0"))
```

### 3.2 管理员命令

| 命令 | 功能 |
|------|------|
| `/admin` | 打开管理员控制面板（按钮交互） |

### 3.3 管理员面板功能

| 功能 | 说明 |
|------|------|
| 📢 群发消息 | 向所有用户发送消息 |
| 📊 统计信息 | 查看用户数等统计 |

---

## 4. 文件与核心函数速查手册

### 4.1 db_manager.py

| 函数签名 | 入参 | 返回值 | 作用 |
|----------|------|--------|------|
| `init_db()` | - | `None` | 初始化数据库，创建表结构 |
| `add_user(uid: int)` | 用户 ID | `None` | 插入新用户（存在则忽略） |
| `add_subscription(uid, exchange, symbol, timeframe, indicator, params)` | 订阅配置 | `int` (sub_id) | 插入一条订阅记录 |
| `get_active_subs()` | - | `Dict[str, List[Dict]]` | 查询所有活跃订阅，按 exchange:symbol:timeframe 归类 |
| `get_user_sub_count(uid: int)` | 用户 ID | `int` | 查询用户订阅数量（用于配额校验） |
| `get_user_subs(uid: int)` | 用户 ID | `List[Dict]` | 查询指定用户的所有订阅记录 |
| `delete_subscription(sub_id: int, uid: int)` | sub_id, 用户ID | `bool` | 删除指定用户的订阅记录 |
| `get_user_language(uid: int)` | 用户 ID | `str` | 查询用户语言设置 |
| `set_user_language(uid: int, lang: str)` | 用户ID, 语言 | `None` | 设置用户语言 |
| `get_total_users()` | - | `int` | 查询总用户数 |

---

### 4.2 market_engine.py

| 函数签名 | 入参 | 返回值 | 作用 |
|----------|------|--------|------|
| `calculate_ema(series: pd.Series, length: int)` | 价格序列、周期 | `pd.Series` | 计算 EMA 指数移动平均线 |
| `calculate_bbands(series: pd.Series, length: int, std: float)` | 价格序列、周期、标准差倍数 | `dict` (upper/middle/lower) | 计算布林带 |
| `fetch_and_calc(exchange_name, symbol, timeframe, retry_count=0)` | 交易所、交易对、周期、重试次数 | `Optional[Dict]` | 抓取 200 根 K 线，计算指标，返回最新一行 |
| `write_cache_atomic(data: Dict)` | 行情数据字典 | `None` | 原子写入缓存文件（带锁+临时文件重命名） |
| `run_engine(subs_list: List[Dict])` | 订阅列表 | `None` | 主循环调度：去重 → 抓取 → 休眠 → 写入缓存 |

**全局常量：**

```python
CACHE_FILE = "cryptosentinel_cache.json"
_cache_lock = asyncio.Lock()
REQUEST_TIMEOUT = 10          # 请求超时 10 秒
MAX_RETRIES = 3               # 最大重试次数
BASE_SLEEP = 1                # 基础休眠 1 秒
```

---

### 4.3 notifier.py

| 函数签名 | 入参 | 返回值 | 作用 |
|----------|------|--------|------|
| `get_bot()` | - | `Bot` | 获取 Telegram Bot 实例（单例） |
| `send_telegram_message(uid, msg, retry_count)` | 用户ID、消息、重试次数 | `bool` | 发送真实 TG 消息（支持重试） |
| `load_market_cache()` | - | `Dict` | 读取 cryptosentinel_cache.json（带锁） |
| `check_bb_signal_change(market_data, prev_state)` | 行情数据、上次状态 | `Optional[bool]` | 检查 BB 状态变化（True=新突破，False=突破消失，None=无变化） |
| `check_vegas_signal_change(market_data, prev_state)` | 行情数据、上次状态 | `Optional[bool]` | 检查 VEGAS 状态变化（True=新多头，False=多头消失，None=无变化） |
| `check_signal(market_data, sub, prev_state)` | 行情数据、订阅规则、上次状态 | `Optional[str]` | 根据指标类型检测状态变化，返回消息文本 |
| `update_signal_state(sub_id, market_data, indicator)` | 订阅ID、行情数据、指标类型 | `None` | 更新信号状态缓存 |
| `watch_and_notify()` | - | `None` | 主监控循环（5 秒间隔，基于 K 线 timestamp 去重） |
| `send_worker()` | - | `None` | 消费队列 worker，调用 send_telegram_message 发送消息 |

**全局变量：**

```python
message_queue = asyncio.Queue()  # 异步消息队列
_cache_lock = asyncio.Lock()     # 文件读取锁
_signal_state = {}               # 信号状态缓存，防止重复触发
_bot_instance = None             # Telegram Bot 实例（单例）
```

---

### 4.4 bot.py

| 函数签名 | 入参 | 返回值 | 作用 |
|----------|------|--------|------|
| `start(update, context)` | TG Update/Context | `int` (状态码) | /start 命令入口，配额校验 |
| `exchange_callback(update, context)` | TG Update/Context | `int` | State 1: 处理交易所选择 |
| `symbol_received(update, context)` | TG Update/Context | `int` | State 2: 处理交易对输入 |
| `timeframe_callback(update, context)` | TG Update/Context | `int` | State 3: 处理周期选择 |
| `indicator_callback(update, context)` | TG Update/Context | `int` | State 4: 处理指标选择 |
| `confirm_callback(update, context)` | TG Update/Context | `int` | State 5: 确认并保存到数据库 |
| `cancel(update, context)` | TG Update/Context | `int` | 取消对话 |
| `list_subs(update, context)` | TG Update/Context | `None` | /list 命令，查看用户订阅列表 |
| `delete_sub(update, context)` | TG Update/Context | `None` | /delete 命令，删除指定订阅 |
| `donate(update, context)` | TG Update/Context | `None` | /donate 命令，显示打赏地址 |
| `show_help(update, context)` | TG Update/Context | `None` | /help 命令 |
| `admin_panel(update, context)` | TG Update/Context | `None` | /admin 命令，管理员面板 |
| `error_handler(update, context)` | TG Update/Context | `None` | 全局异常处理 |
| `safe_reply(update, text, markup)` | Update/文本/键盘 | `None` | 安全发送消息（兼容 message/callback_query） |
| `safe_edit(update, text, markup)` | Update/文本/键盘 | `None` | 安全编辑消息 |
| `main()` | - | `None` | Bot 启动入口 |

**命令列表：**

| 命令 | 用法 | 功能 |
|------|------|------|
| `/start` | `/start` | 启动添加监控流程 |
| `/list` | `/list` | 查看当前用户所有监控任务 |
| `/delete` | `/delete [编号]` | 删除指定编号的监控任务 |
| `/donate` | `/donate` | 显示打赏地址 |
| `/help` | `/help` | 查看命令帮助 |
| `/cancel` | `/cancel` | 取消当前对话 |

**全局常量：**

```python
MAX_SUBSCRIPTIONS = 10          # 单用户最大订阅数
CONVERSATION_TIMEOUT = 120      # 对话超时 120 秒
# 状态机状态
EXCHANGE, SYMBOL, TIMEFRAME, INDICATOR, CONFIRM = range(5)
```

---

## 5. 数据结构契约

### 5.1 cryptosentinel_cache.json 标准结构

```json
{
  "OKX:BTC/USDT:15m": {
    "exchange": "OKX",
    "symbol": "BTC/USDT",
    "timeframe": "15m",
    "timestamp": 1709280000000,
    "open": 51234.5,
    "high": 51500.0,
    "low": 51000.0,
    "close": 51350.0,
    "volume": 1234.56,
    "BBL_20_2": 50800.0,
    "BBM_20_2": 51000.0,
    "BBU_20_2": 51200.0,
    "EMA_144": 50950.0,
    "EMA_169": 50880.0
  },
  "OKX:BTC/USDT:1h": {
    "exchange": "OKX",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "timestamp": 1709276400000,
    "open": 51000.0,
    "high": 51500.0,
    "low": 50800.0,
    "close": 51200.0,
    "volume": 2345.67,
    "BBL_20_2": 50500.0,
    "BBM_20_2": 50800.0,
    "BBU_20_2": 51100.0,
    "EMA_144": 50700.0,
    "EMA_169": 50600.0
  },
  "Binance:ETH/USDT:1h": {
    "exchange": "Binance",
    "symbol": "ETH/USDT",
    "timeframe": "1h",
    "timestamp": 1709276400000,
    "open": 2890.5,
    "high": 2910.0,
    "low": 2880.0,
    "close": 2905.0,
    "volume": 5678.9,
    "BBL_20_2": 2850.0,
    "BBM_20_2": 2875.0,
    "BBU_20_2": 2900.0,
    "EMA_144": 2885.0,
    "EMA_169": 2870.0
  }
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| Key | String | `exchange:symbol:timeframe` 格式（v1.6 更新） |
| `exchange` | String | 交易所名称 |
| `symbol` | String | 交易对 |
| `timeframe` | String | K 线周期 |
| `timestamp` | Integer | K 线时间戳（毫秒） |
| `open/high/low/close/volume` | Float | OHLCV 数据 |
| `BBL_20_2` | Float/null | 布林带下轨 |
| `BBM_20_2` | Float/null | 布林带中轨 |
| `BBU_20_2` | Float/null | 布林带上轨 |
| `EMA_144` | Float/null | EMA 144 |
| `EMA_169` | Float/null | EMA 169 |

---

## 6. 核心规范与续写红线

### 6.1 强制规范

#### ✅ 必须使用 asyncio

- 全链路必须使用 `async/await`，禁止使用阻塞式 `time.sleep()`。
- 所有休眠必须使用 `await asyncio.sleep()`。

```python
# ✅ 正确
await asyncio.sleep(5)

# ❌ 错误
time.sleep(5)
```

#### ✅ 必须开启 ccxt 限流

```python
exchange = ccxt.okx({
    "enableRateLimit": True,  # 必须开启
})
```

#### ✅ 必须处理 DataFrame 内存释放

```python
# ✅ 正确：finally 块显式删除
df = None
try:
    df = pd.DataFrame(...)
    # ... 计算逻辑
finally:
    if df is not None:
        del df
```

#### ✅ 文件读写必须加锁

```python
# ✅ 正确：使用 asyncio.Lock
_cache_lock = asyncio.Lock()

async def write_cache_atomic(data):
    async with _cache_lock:
        # 写入逻辑
```

---

### 6.2 续写红线（禁止违反）

| 序号 | 规则 | 违规后果 |
|------|------|----------|
| 1 | 禁止使用 `time.sleep()` | 阻塞事件循环，导致单核性能归零 |
| 2 | 禁止在主循环中不使用 `await asyncio.sleep()` | 循环无间隔，触发交易所限流封禁 |
| 3 | 禁止不调用 `exchange.close()` | 连接泄漏，内存持续增长 |
| 4 | 禁止不删除 DataFrame | 1G 内存 VPS 溢出崩溃 |
| 5 | 禁止不开启 `enableRateLimit` | IP 被交易所拉黑，全线崩溃 |
| 6 | 禁止不添加文件锁 | JSON 读写冲突，缓存损坏 |
| 7 | 禁止不使用 try-except 包裹网络请求 | 单币异常导致全链路崩溃 |
| 8 | 禁止在 bot 状态机中不做 None 检查 | 用户异常输入导致服务崩溃 |

---

### 6.3 部署建议

- **进程管理**：使用 PM2 守护 3 个独立进程：
  - `bot.py` - 前端交互
  - `run_engine_loop.py` - 行情引擎
  - `notifier.py` - 信号推送
- **运行周期**：
  - `market_engine`：建议 30~60 秒执行一次 `run_engine()`
  - `notifier`：建议 5 秒执行一次 `watch_and_notify()`
- **监控指标**：监控 `cryptosentinel_cache.json` 文件更新时间，确保行情引擎正常运行。

---

## 7. 环境变量配置

### 7.1 必需配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | `1234567890:ABCdef...` |
| `ADMIN_UID` | 管理员 Telegram UID | `123456789` |
| `DONATE_ADDRESS` | 打赏地址 (TRC20) | `TQ66Jy...` |

### 7.2 配置方式

**方式一：环境变量**
```bash
export TELEGRAM_BOT_TOKEN="your_token_here"
export ADMIN_UID="your_telegram_uid"
export DONATE_ADDRESS="your_trc20_wallet_address"
```

**方式二：.env 文件**
```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件
TELEGRAM_BOT_TOKEN=your_token_here
ADMIN_UID=your_telegram_uid
DONATE_ADDRESS=your_trc20_wallet_address
```

---

## 8. 已修复的关键问题

### 8.1 信号重复触发问题 (v1.1 已修复)

**问题描述**: 之前的实现每 5 秒检查一次信号，导致同一根 K 线期间重复发送消息。

**修复方案**: 
- 新增 `_signal_state` 缓存，记录每个订阅的上次状态
- 基于 `timestamp` 判断 K 线是否更新
- 只在状态从 False 变为 True 时触发信号

### 8.2 缓存覆盖丢失问题 (v1.1 已修复)

**问题描述**: 之前 `write_cache_atomic` 会完全覆盖缓存，导致本次抓取失败的标的数据丢失。

**修复方案**:
- 写入前先读取现有缓存
- 合并新旧数据后再写入

### 8.3 Exchange 未关闭问题 (v1.1 已修复)

**问题描述**: 网络异常时 exchange 实例可能未被关闭，导致连接泄漏。

**修复方案**:
- 将 `exchange.close()` 移至 finally 块
- 确保所有情况下都能正确关闭

### 8.4 SQLite 并发锁问题 (v1.1 已修复)

**问题描述**: 多进程同时操作数据库可能导致 `database is locked` 错误。

**修复方案**:
- 启用 WAL 模式: `PRAGMA journal_mode=WAL`
- 设置超时: `PRAGMA busy_timeout=5000`

### 8.5 真实 TG 推送实现 (v1.2 已实现)

**之前状态**: 使用 `mock_send_tg` 模拟发送，生产环境不可用。

**实现方案**:
- 新增 `send_telegram_message()` 函数，调用真实 Telegram API
- 新增 `get_bot()` 单例获取 Bot 实例
- 支持限流重试（`RetryAfter` 异常自动等待重试）
- 支持超时重试（最多 3 次）
- 使用环境变量 `TELEGRAM_BOT_TOKEN` 获取 Token

### 8.6 多语言系统 (v1.4 已实现)

**功能说明**: 支持中英文切换，用户可随时切换语言。

**实现内容**:
- 新增 `locales/zh.py`, `locales/en.py` 语言包
- 新增 `i18n.py` 国际化工具函数
- 用户命令：`/language` 切换语言
- 自动检测：首次使用根据 Telegram `language_code` 自动选择语言
- 语言存储：保存到 `users.language` 字段

### 8.7 VEGAS 触碰检测 (v1.5 已实现)

**之前状态**: VEGAS 为趋势判断（EMA144 > EMA169 触发一次），不是实际触碰。

**改进方案**:
- 检测 K 线影线是否触碰 EMA144 或 EMA169
- 区分上穿和下穿信号
- 使用 `high`、`low` 和 `close` 判断是否穿过 EMA 线
- 同一根 K 线内不重复触发

**信号类型**:
- ⬆️ 上穿 EMA144：`low < EMA144 < high` 且 `close > EMA144`
- ⬇️ 下穿 EMA144：`low < EMA144 < high` 且 `close < EMA144`
- ⬆️ 上穿 EMA169：`low < EMA169 < high` 且 `close > EMA169`
- ⬇️ 下穿 EMA169：`low < EMA169 < high` 且 `close < EMA169`

### 8.8 币种白名单验证 (v1.5 已实现)

**之前状态**: 用户可输入任意交易对，不存在的币种抓取时静默失败。

**改进方案**:
- 从 OKX API 获取支持的交易对列表
- 缓存 1 小时，避免频繁请求
- 用户输入不支持的币种时，显示热门币种列表
- 只验证 OKX，Binance 暂不验证

### 8.9 缓存 Key 时间周期问题 (v1.6 已修复)

**问题描述**: 缓存 key 格式为 `exchange:symbol`，不包含 timeframe。当同一币种有多个时间周期订阅时，后抓取的数据会覆盖前一个，导致用户收到错误周期的数据。

**修复方案**:
- 缓存 key 改为 `exchange:symbol:timeframe` 格式
- `get_active_subs()` 分组 key 同步更新
- 支持同一币种多个时间周期独立存储

### 8.10 VEGAS 信号逻辑错误 (v1.6 已修复)

**问题描述**: 上穿和下穿信号使用相同条件 `low < EMA < high`，无法区分方向，导致同时触发两个信号。

**修复方案**:
- 上穿信号：`low < EMA < high` 且 `close > EMA`（收盘价在 EMA 上方）
- 下穿信号：`low < EMA < high` 且 `close < EMA`（收盘价在 EMA 下方）

### 8.11 敏感信息硬编码问题 (v1.6 已修复)

**问题描述**: 管理员 UID 和充值地址硬编码在源码中，存在安全风险且不便于配置。

**修复方案**:
- `ADMIN_UID` 从环境变量读取
- `DONATE_ADDRESS` 从环境变量读取
- 新增 `.env.example` 配置模板

### 8.12 功能菜单改造 (v2.0 已实现)

**之前状态**: `/start` 直接进入订阅流程，没有功能菜单。

**改进方案**:
- `/start` 显示功能菜单，包含按钮
- 添加"联系开发者"功能
- 添加"打赏开发者"功能
- 所有功能页面都有返回按钮

**菜单按钮**:
- ➕ 添加监控
- 📋 我的监控
- 🆔 我的UID
- 👨‍💻 联系开发者
- 🌐 语言
- ☕ 打赏开发者
- ❓ 帮助

### 8.13 布林带影线触碰 (v2.0 已实现)

**之前状态**: 只检测收盘价是否突破布林上轨。

**改进方案**:
- 检测 K 线最高价是否触碰布林上轨
- 更敏感的信号触发
- 通知消息显示最高价和收盘价

**触发条件**: `high > BBU_20_2`

### 8.14 命令自动补全 (v2.0 已实现)

**功能说明**: 输入 `/` 自动显示命令列表。

**实现方式**: 使用 Telegram Bot API 的 `set_my_commands`。

**命令列表**:
| 命令 | 描述 |
|------|------|
| /start | 主菜单 |
| /list | 我的监控 |
| /donate | 打赏开发者 |
| /myid | 我的UID |
| /language | 切换语言 |
| /help | 帮助 |

### 8.15 快捷交易对按钮 (v2.0 已实现)

**功能说明**: 选择交易所后显示 BTC/USDT 和 ETH/USDT 快捷按钮。

**实现方式**:
- 选择交易所后显示快捷按钮
- 点击按钮直接进入周期选择
- 也可手动输入其他交易对

### 8.16 非指令消息处理 (v2.0 已实现)

**之前状态**: 非指令消息被忽略或转发给群发处理器。

**改进方案**:
- 用户发送非指令文本时返回帮助信息
- 更友好的用户体验

### 8.17 VIP 系统移除 (v3.0 已实现)

**改进内容**:
- 移除 VIP 会员系统，简化为统一配额（每用户 10 个监控）
- 将充值地址改为打赏地址，新增 `/donate` 命令
- 删除 VIP 相关数据库表（payments、system_config、free_vip_given）
- 删除 vip_checker.py 进程
- 保留管理员群发和统计功能

---

*文档版本：v3.0*  
*最后更新：2026-04-08*