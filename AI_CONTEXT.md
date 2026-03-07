# AI_CONTEXT.md

> 本文档供 AI Coding 助手阅读，无需面向人类的解释。

---

## 1. Tech Stack & Versions

```
Python: 3.10+
aiosqlite>=0.19.0
ccxt>=4.0.0
pandas>=2.0.0
numpy>=1.24.0
python-telegram-bot>=20.0
```

**运行环境**:
- PM2 进程管理
- 4 个独立进程: bot, engine, notifier, vip_checker
- SQLite WAL 模式

---

## 2. System Architecture

### 2.1 进程拓扑

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│   bot.py    │     │ run_engine_loop │     │  notifier.py │     │vip_checker.py│
│ (前端交互)   │     │  + market_engine│     │  (信号消费)   │     │  (VIP检测)   │
└──────┬──────┘     └────────┬────────┘     └──────┬───────┘     └──────┬───────┘
       │                     │                     │                    │
       ▼                     ▼                     ▼                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          SQLite (cryptosentinel.db)                          │
│                 users / subscriptions / payments / system_config             │
└──────────────────────────────────────────────────────────────────────────────┘
       │                     ▲                     ▲
       │                     │                     │
       ▼                     │                     │
┌──────────────────┐         │                     │
│ context.user_data│         │                     │
│  (会话状态临时)   │         │                     │
└──────────────────┘         │                     │
                             │                     │
                    ┌────────┴─────────┐           │
                    │cryptosentinel_   │           │
                    │   cache.json     │───────────┘
                    └──────────────────┘
```

### 2.2 通信契约

| 生产者 | 消费者 | 介质 | 格式 |
|--------|--------|------|------|
| bot.py | market_engine | SQLite subscriptions 表 | INSERT/UPDATE |
| market_engine.py | notifier.py | cryptosentinel_cache.json | `{"EXCHANGE:SYMBOL:TIMEFRAME": {...}}` |
| notifier.py | 用户 | Telegram API | HTML 消息 |
| bot.py | 管理员 | Telegram API | 充值通知 |

### 2.3 缓存文件结构 (cryptosentinel_cache.json)

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
  }
}
```

**Key 格式**: `exchange:symbol:timeframe` (区分大小写，symbol 包含 `/`)

---

## 3. Database Schema (SQLite)

### 3.1 users 表

```sql
CREATE TABLE users (
    uid INTEGER PRIMARY KEY,           -- Telegram 用户 ID
    is_vip BOOLEAN DEFAULT 0,          -- VIP 状态 (0/1)
    vip_expire_at TIMESTAMP,           -- VIP 到期时间 (ISO 格式)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deposit_address TEXT,              -- 预留：专属充值地址
    notes TEXT,                        -- 备注
    language TEXT DEFAULT 'zh'         -- 语言设置 (zh/en)
);
```

### 3.2 subscriptions 表

```sql
CREATE TABLE subscriptions (
    sub_id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid INTEGER,                       -- 外键 -> users.uid
    exchange TEXT NOT NULL,            -- 交易所 (OKX/Binance)
    symbol TEXT NOT NULL,              -- 交易对 (BTC/USDT)
    timeframe TEXT NOT NULL,           -- 周期 (15m/1h/4h)
    indicator TEXT NOT NULL,           -- 指标 (BB/VEGAS)
    params TEXT,                       -- JSON 参数
    is_active BOOLEAN DEFAULT 1,       -- 是否激活
    FOREIGN KEY (uid) REFERENCES users(uid)
);
```

**params 示例**:
- BB: `{"period": 20, "std_dev": 2}`
- VEGAS: `{"ema_fast": 144, "ema_slow": 169}`

### 3.3 payments 表

```sql
CREATE TABLE payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid INTEGER NOT NULL,
    tx_hash TEXT NOT NULL,             -- TRC20 交易哈希
    amount REAL,                       -- 金额 (可为空)
    status TEXT DEFAULT 'pending',     -- pending/confirmed/rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,             -- 审核时间
    admin_notes TEXT,
    FOREIGN KEY (uid) REFERENCES users(uid)
);
```

### 3.4 system_config 表

```sql
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

**预设 Key**:
- `vip_price_usdt`: VIP 价格
- `vip_duration_days`: VIP 天数
- `deposit_address`: 充值地址

### 3.5 free_vip_given 表

```sql
CREATE TABLE free_vip_given (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    given_count INTEGER DEFAULT 0       -- 已赠送免费 VIP 数量
);
```

---

## 4. File Topology & Core Functions

### 4.1 bot.py (Telegram Bot 前端)

```python
# 全局常量
DEPOSIT_ADDRESS: str
SUPPORTED_SYMBOLS_CACHE: set
SUPPORTED_SYMBOLS_CACHE_TIME: int
SUPPORTED_SYMBOLS_CACHE_TTL: int = 3600

# 状态机状态
EXCHANGE, SYMBOL, TIMEFRAME, INDICATOR, CONFIRM, DEPOSIT_TX_HASH, BROADCAST_MESSAGE = range(7)
CONVERSATION_TIMEOUT: int = 120

# 核心异步函数
async def fetch_okx_symbols() -> set
async def get_supported_symbols() -> set
async def get_lang(update: Update) -> str
async def safe_reply(update: Update, text: str, reply_markup: Optional[InlineKeyboardMarkup], parse_mode: Optional[str]) -> None
async def safe_edit(update: Update, text: str, reply_markup: Optional[InlineKeyboardMarkup], parse_mode: Optional[str]) -> None
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int
async def add_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None
async def add_flow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None
async def exchange_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int
async def symbol_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int
async def timeframe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int
async def indicator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int
async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int
async def list_subs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None
async def delete_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None
async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None
async def mystatus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None
async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None
async def admin_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None
def main() -> None
```

### 4.2 db_manager.py (数据库管理)

```python
# 全局常量
DATABASE_NAME: str
ADMIN_UID: int                          # 从环境变量读取
DEPOSIT_ADDRESS: str                    # 从环境变量读取
VIP_PRICE_USDT: int = 10
VIP_DURATION_DAYS: int = 365
MAX_SUBSCRIPTIONS_FREE: int = 1
MAX_SUBSCRIPTIONS_VIP: int = 5
FREE_VIP_USERS_LIMIT: int = 50
FREE_VIP_DURATION_DAYS: int = 14

# 核心异步函数
async def init_db() -> None
async def get_config(key: str) -> Optional[str]
async def set_config(key: str, value: str) -> None
async def get_vip_price() -> float
async def get_vip_duration() -> int
async def get_deposit_address() -> str
async def add_user(uid: int) -> None
async def add_subscription(uid: int, exchange: str, symbol: str, timeframe: str, indicator: str, params: Optional[Dict]) -> int
async def get_active_subs() -> Dict[str, List[Dict[str, Any]]]
async def get_user_sub_count(uid: int) -> int
async def get_user_subs(uid: int) -> List[Dict[str, Any]]
async def delete_subscription(sub_id: int, uid: int) -> bool
async def get_user_info(uid: int) -> Optional[Dict[str, Any]]
async def set_user_vip(uid: int, days: int, admin_notes: str = None) -> bool
async def check_and_update_vip_status() -> List[int]
async def get_expiring_vip_users(days: int) -> List[Dict[str, Any]]
async def get_max_subscriptions(uid: int) -> int
async def create_payment_request(uid: int, tx_hash: str, amount: float = None) -> int
async def get_pending_payments() -> List[Dict[str, Any]]
async def get_payment(payment_id: int) -> Optional[Dict[str, Any]]
async def approve_payment(payment_id: int, admin_uid: int) -> bool
async def reject_payment(payment_id: int, admin_uid: int, reason: str = None) -> bool
async def get_all_users_count() -> int
async def get_vip_users_count() -> int
async def get_all_users() -> List[int]
async def get_vip_users() -> List[Dict[str, Any]]
async def get_user_rank(uid: int) -> Optional[int]
async def get_free_vip_given_count() -> int
async def increment_free_vip_count() -> None
async def try_give_free_vip(uid: int) -> bool
async def get_user_language(uid: int) -> str
async def set_user_language(uid: int, language: str) -> None
```

### 4.3 market_engine.py (行情数据生产)

```python
# 全局常量
CACHE_FILE: str                        # cryptosentinel_cache.json
_cache_lock: asyncio.Lock
REQUEST_TIMEOUT: int = 10
MAX_RETRIES: int = 3
BASE_SLEEP: int = 1

# 同步计算函数
def calculate_ema(series: pd.Series, length: int) -> pd.Series
def calculate_bbands(series: pd.Series, length: int = 20, std: float = 2) -> dict

# 核心异步函数
async def fetch_and_calc(exchange_name: str, symbol: str, timeframe: str, retry_count: int = 0) -> Optional[Dict[str, Any]]
async def load_existing_cache() -> Dict[str, Any]
async def write_cache_atomic(data: Dict[str, Any]) -> None
async def run_engine(subs_list: List[Dict[str, Any]]) -> None
```

### 4.4 notifier.py (信号监控与推送)

```python
# 全局变量
CACHE_FILE: str
message_queue: asyncio.Queue
_cache_lock: asyncio.Lock
_signal_state: Dict[int, Dict[str, Any]]    # 信号状态缓存
_bot_instance: Optional[Bot]

# 核心异步函数
async def get_bot() -> Bot
async def send_telegram_message(uid: int, msg: str, retry_count: int = 0) -> bool
async def mock_send_tg(uid: int, msg: str) -> bool
async def load_market_cache() -> Dict[str, Any]

# 同步信号检测函数
def check_bb_signal_change(market_data: Dict, prev_state: Optional[Dict]) -> Optional[bool]
def check_vegas_signal_change(market_data: Dict, prev_state: Optional[Dict]) -> List[str]
def check_signal(market_data: Dict, sub: Dict, prev_state: Optional[Dict]) -> Optional[str]
def update_signal_state(sub_id: int, market_data: Dict, indicator: str) -> None

# 主循环
async def watch_and_notify() -> None
async def send_worker() -> None
async def main() -> None
```

### 4.5 vip_checker.py (VIP 到期检测)

```python
# 核心异步函数
async def get_bot() -> Bot
async def send_vip_reminder(uid: int, days_left: int) -> bool
async def send_expired_notification(uid: int) -> bool
async def check_vip_expiry() -> None
async def vip_checker_loop() -> None              # 每小时执行
async def main() -> None
```

### 4.6 run_engine_loop.py (行情引擎循环入口)

```python
# 全局常量
ENGINE_INTERVAL: int = 30

# 核心异步函数
async def main() -> None
```

### 4.7 i18n.py (国际化工具)

```python
# 全局常量
LANGUAGES: Dict[str, Dict]
DEFAULT_LANGUAGE: str = "zh"

# 同步函数
def get_message(key: str, lang: str = "zh", **kwargs) -> str
def detect_language(language_code: Optional[str]) -> str
def get_button_text(key: str, lang: str = "zh") -> str
```

---

## 5. Strict AI Coding Rules

### 5.1 异步红线

```python
# ✅ 正确
await asyncio.sleep(5)

# ❌ 禁止 - 阻塞事件循环
time.sleep(5)
```

### 5.2 内存管理红线

```python
# ✅ 正确 - DataFrame 用完必须删除
df = None
try:
    df = pd.DataFrame(...)
    # ... 计算逻辑
finally:
    if df is not None:
        del df

# ❌ 禁止 - DataFrame 驻留内存
df = pd.DataFrame(...)
# 使用后未删除
```

### 5.3 文件读写红线

```python
# ✅ 正确 - 必须加锁
async with _cache_lock:
    with open(CACHE_FILE, "r") as f:
        data = json.load(f)

# ❌ 禁止 - 无锁并发读写
with open(CACHE_FILE, "r") as f:
    data = json.load(f)
```

### 5.4 Exchange 实例红线

```python
# ✅ 正确 - finally 块关闭
exchange = None
try:
    exchange = ccxt.okx({"enableRateLimit": True})
    # ... 操作
finally:
    if exchange is not None:
        await exchange.close()

# ❌ 禁止 - 未关闭导致连接泄漏
exchange = ccxt.okx({"enableRateLimit": True})
# ... 操作后未关闭
```

### 5.5 CCXT 限流红线

```python
# ✅ 正确 - 必须开启限流
exchange = ccxt.okx({"enableRateLimit": True})

# ❌ 禁止 - 未开启限流可能被封 IP
exchange = ccxt.okx({})
```

### 5.6 SQLite 并发红线

```python
# ✅ 正确 - 启用 WAL 模式
await db.execute("PRAGMA journal_mode=WAL")
await db.execute("PRAGMA busy_timeout=5000")

# ❌ 禁止 - 默认模式并发写入会锁死
# 不设置 PRAGMA
```

### 5.7 None 检查红线

```python
# ✅ 正确 - 所有可能为 None 的值必须检查
market_data = await load_market_cache()
if market_data is None:
    return

# ❌ 禁止 - 未检查直接使用
market_data = await load_market_cache()
symbol = market_data["symbol"]  # 可能 KeyError
```

### 5.8 缓存 Key 格式红线

```python
# ✅ 正确 - 包含 timeframe
key = f"{exchange}:{symbol}:{timeframe}"  # "OKX:BTC/USDT:15m"

# ❌ 禁止 - 不含 timeframe (会导致多周期覆盖)
key = f"{exchange}:{symbol}"  # 错误
```

### 5.9 环境变量红线

```python
# ✅ 正确 - 从环境变量读取敏感配置
ADMIN_UID = int(os.environ.get("ADMIN_UID", "0"))
DEPOSIT_ADDRESS = os.environ.get("DEPOSIT_ADDRESS", "")

# ❌ 禁止 - 硬编码敏感信息
ADMIN_UID = 123456789
```

### 5.10 信号去重红线

```python
# ✅ 正确 - 基于 timestamp 去重
if current_timestamp == prev_timestamp:
    continue  # 同一根 K 线不重复触发

# ❌ 禁止 - 无去重逻辑
# 每次检查都触发信号
```

---

## 6. VIP 系统业务规则

| 规则 | 值 |
|------|-----|
| VIP 价格 | 10 USDT |
| VIP 时长 | 365 天 |
| 普通用户配额 | 1 个指标 |
| VIP 用户配额 | 5 个指标 |
| 免费赠送名额 | 前 50 名用户 |
| 免费赠送时长 | 14 天 |
| 充值确认方式 | 管理员手动批准 |
| 到期提醒 | 7天、3天 |

---

## 7. 支持的指标

| 指标 | Key | 参数 | 触发条件 |
|------|-----|------|----------|
| BB 布林带 | `BB` | `period: 20, std_dev: 2` | 最高价 > 布林上轨 |
| VEGAS 通道 | `VEGAS` | `ema_fast: 144, ema_slow: 169` | K线影线触碰 EMA144/169 |

---

## 8. 添加新指标流程

1. `market_engine.py`: 添加计算函数 → 在 `fetch_and_calc()` 中调用 → 写入 result
2. `notifier.py`: 添加 `check_xxx_signal_change()` → 在 `check_signal()` 中添加分支 → 更新 `update_signal_state()`
3. `bot.py`: 在 `add_flow_callback()` 中添加按钮 → 添加参数配置
4. `locales/zh.py` `en.py`: 添加消息模板

---

*文档版本: 2.0*
*生成时间: 2026-03-07*