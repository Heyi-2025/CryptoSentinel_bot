"""
数据库管理模块
负责 SQLite 数据库的异步增删改查操作
"""
import asyncio
import aiosqlite
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DATABASE_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cryptosentinel.db")

ADMIN_UID = 7033823445

DEPOSIT_ADDRESS = "TQ66Jy7fgubE9H3dj981gfqnEfodSBVPfx"

VIP_PRICE_USDT = 10
VIP_DURATION_DAYS = 365

MAX_SUBSCRIPTIONS_FREE = 1
MAX_SUBSCRIPTIONS_VIP = 5

FREE_VIP_USERS_LIMIT = 50
FREE_VIP_DURATION_DAYS = 14


async def init_db() -> None:
    """
    初始化数据库，创建所有表
    启用 WAL 模式以提高并发性能
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                uid INTEGER PRIMARY KEY,
                is_vip BOOLEAN DEFAULT 0,
                vip_expire_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deposit_address TEXT,
                notes TEXT,
                language TEXT DEFAULT 'zh'
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                sub_id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid INTEGER,
                exchange TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                indicator TEXT NOT NULL,
                params TEXT,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (uid) REFERENCES users(uid)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid INTEGER NOT NULL,
                tx_hash TEXT NOT NULL,
                amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                admin_notes TEXT,
                FOREIGN KEY (uid) REFERENCES users(uid)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS free_vip_given (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                given_count INTEGER DEFAULT 0
            )
        """)
        
        await db.execute("""
            INSERT OR IGNORE INTO system_config (key, value) VALUES 
                ('vip_price_usdt', ?),
                ('vip_duration_days', ?),
                ('deposit_address', ?)
        """, (str(VIP_PRICE_USDT), str(VIP_DURATION_DAYS), DEPOSIT_ADDRESS))
        
        await db.execute("""
            INSERT OR IGNORE INTO free_vip_given (id, given_count) VALUES (1, 0)
        """)
        
        await db.commit()


async def get_config(key: str) -> Optional[str]:
    """
    获取系统配置
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute(
            "SELECT value FROM system_config WHERE key = ?",
            (key,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def set_config(key: str, value: str) -> None:
    """
    设置系统配置
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()


async def get_vip_price() -> float:
    """获取 VIP 价格"""
    value = await get_config('vip_price_usdt')
    return float(value) if value else VIP_PRICE_USDT


async def get_vip_duration() -> int:
    """获取 VIP 时长（天）"""
    value = await get_config('vip_duration_days')
    return int(value) if value else VIP_DURATION_DAYS


async def get_deposit_address() -> str:
    """获取充值地址"""
    value = await get_config('deposit_address')
    return value if value else DEPOSIT_ADDRESS


async def add_user(uid: int) -> None:
    """
    插入新用户，如果用户已存在则忽略
    
    Args:
        uid: 用户 ID
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (uid, is_vip) VALUES (?, 0)",
            (uid,)
        )
        await db.commit()


async def add_subscription(
    uid: int,
    exchange: str,
    symbol: str,
    timeframe: str,
    indicator: str,
    params: Optional[Dict[str, Any]] = None
) -> int:
    """
    插入一条订阅记录
    
    Args:
        uid: 用户 ID
        exchange: 交易所名称 (如 OKX, Binance)
        symbol: 交易对 (如 BTC/USDT)
        timeframe: 时间周期 (如 15m, 1h)
        indicator: 指标名称 (如 BB, RSI, MACD)
        params: 指标参数字典
    
    Returns:
        新插入记录的 sub_id
    """
    params_json = json.dumps(params) if params else "{}"
    
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute(
            """
            INSERT INTO subscriptions 
            (uid, exchange, symbol, timeframe, indicator, params, is_active) 
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (uid, exchange, symbol, timeframe, indicator, params_json)
        )
        await db.commit()
        return cursor.lastrowid or 0


async def get_active_subs() -> Dict[str, List[Dict[str, Any]]]:
    """
    查询所有处于 active 状态的订阅记录，按 exchange 和 symbol 归类去重
    
    Returns:
        字典，key 为 "exchange:symbol" 格式，value 为订阅配置列表
        示例:
        {
            "OKX:BTC/USDT": [
                {
                    "sub_id": 1,
                    "uid": 123,
                    "exchange": "OKX",
                    "symbol": "BTC/USDT",
                    "timeframe": "15m",
                    "indicator": "BB",
                    "params": {"period": 20}
                }
            ]
        }
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT sub_id, uid, exchange, symbol, timeframe, indicator, params
            FROM subscriptions
            WHERE is_active = 1
            """
        ) as cursor:
            rows = await cursor.fetchall()
    
    result: Dict[str, List[Dict[str, Any]]] = {}
    
    for row in rows:
        key = f"{row['exchange']}:{row['symbol']}"
        params = json.loads(row['params']) if row['params'] else {}
        
        sub_info = {
            "sub_id": row["sub_id"],
            "uid": row["uid"],
            "exchange": row["exchange"],
            "symbol": row["symbol"],
            "timeframe": row["timeframe"],
            "indicator": row["indicator"],
            "params": params
        }
        
        if key not in result:
            result[key] = []
        result[key].append(sub_info)
    
    return result


async def get_user_sub_count(uid: int) -> int:
    """
    查询指定用户的订阅数量
    
    Args:
        uid: 用户 ID
    
    Returns:
        订阅数量
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM subscriptions WHERE uid = ?",
            (uid,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_user_subs(uid: int) -> List[Dict[str, Any]]:
    """
    查询指定用户的所有订阅记录
    
    Args:
        uid: 用户 ID
    
    Returns:
        订阅列表，每项包含 sub_id, exchange, symbol, timeframe, indicator, params
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT sub_id, exchange, symbol, timeframe, indicator, params, is_active
            FROM subscriptions
            WHERE uid = ?
            ORDER BY sub_id DESC
            """,
            (uid,)
        ) as cursor:
            rows = await cursor.fetchall()
    
    result = []
    for row in rows:
        params = json.loads(row["params"]) if row["params"] else {}
        result.append({
            "sub_id": row["sub_id"],
            "exchange": row["exchange"],
            "symbol": row["symbol"],
            "timeframe": row["timeframe"],
            "indicator": row["indicator"],
            "params": params,
            "is_active": row["is_active"]
        })
    
    return result


async def delete_subscription(sub_id: int, uid: int) -> bool:
    """
    删除指定用户的订阅记录
    
    Args:
        sub_id: 订阅记录 ID
        uid: 用户 ID（用于验证归属）
    
    Returns:
        是否删除成功
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute(
            "DELETE FROM subscriptions WHERE sub_id = ? AND uid = ?",
            (sub_id, uid)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_user_info(uid: int) -> Optional[Dict[str, Any]]:
    """
    获取用户信息
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT uid, is_vip, vip_expire_at, created_at FROM users WHERE uid = ?",
            (uid,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "uid": row["uid"],
                    "is_vip": row["is_vip"],
                    "vip_expire_at": row["vip_expire_at"],
                    "created_at": row["created_at"]
                }
            return None


async def set_user_vip(uid: int, days: int, admin_notes: str = None) -> bool:
    """
    设置用户 VIP
    
    Args:
        uid: 用户 ID
        days: VIP 天数
        admin_notes: 管理员备注
    
    Returns:
        是否成功
    """
    now = datetime.now()
    user_info = await get_user_info(uid)
    
    if user_info and user_info.get("vip_expire_at"):
        expire_at = datetime.fromisoformat(user_info["vip_expire_at"])
        if expire_at > now:
            expire_at = expire_at + timedelta(days=days)
        else:
            expire_at = now + timedelta(days=days)
    else:
        expire_at = now + timedelta(days=days)
    
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            INSERT INTO users (uid, is_vip, vip_expire_at) 
            VALUES (?, 1, ?)
            ON CONFLICT(uid) DO UPDATE SET is_vip = 1, vip_expire_at = ?
            """,
            (uid, expire_at.isoformat(), expire_at.isoformat())
        )
        if admin_notes:
            await db.execute(
                "UPDATE users SET notes = ? WHERE uid = ?",
                (admin_notes, uid)
            )
        await db.commit()
    
    return True


async def check_and_update_vip_status() -> List[int]:
    """
    检查并更新所有用户的 VIP 状态
    
    Returns:
        过期的用户 ID 列表
    """
    now = datetime.now()
    expired_uids = []
    
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT uid, vip_expire_at FROM users WHERE is_vip = 1"
        ) as cursor:
            rows = await cursor.fetchall()
        
        for row in rows:
            if row["vip_expire_at"]:
                expire_at = datetime.fromisoformat(row["vip_expire_at"])
                if expire_at <= now:
                    await db.execute(
                        "UPDATE users SET is_vip = 0 WHERE uid = ?",
                        (row["uid"],)
                    )
                    expired_uids.append(row["uid"])
        
        await db.commit()
    
    return expired_uids


async def get_expiring_vip_users(days: int) -> List[Dict[str, Any]]:
    """
    获取即将过期的 VIP 用户
    
    Args:
        days: 剩余天数
    
    Returns:
        用户列表
    """
    now = datetime.now()
    target_date = now + timedelta(days=days)
    
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT uid, vip_expire_at FROM users 
            WHERE is_vip = 1 AND vip_expire_at <= ? AND vip_expire_at > ?
            """,
            (target_date.isoformat(), now.isoformat())
        ) as cursor:
            rows = await cursor.fetchall()
        
        return [{"uid": row["uid"], "vip_expire_at": row["vip_expire_at"]} for row in rows]


async def get_max_subscriptions(uid: int) -> int:
    """
    获取用户的最大订阅数
    """
    user_info = await get_user_info(uid)
    if user_info and user_info.get("is_vip"):
        return MAX_SUBSCRIPTIONS_VIP
    return MAX_SUBSCRIPTIONS_FREE


async def create_payment_request(uid: int, tx_hash: str, amount: float = None) -> int:
    """
    创建充值申请
    
    Returns:
        payment_id
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute(
            """
            INSERT INTO payments (uid, tx_hash, amount, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (uid, tx_hash, amount)
        )
        await db.commit()
        return cursor.lastrowid or 0


async def get_pending_payments() -> List[Dict[str, Any]]:
    """
    获取待处理的充值申请
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT p.payment_id, p.uid, p.tx_hash, p.amount, p.created_at
            FROM payments p
            WHERE p.status = 'pending'
            ORDER BY p.created_at DESC
            """
        ) as cursor:
            rows = await cursor.fetchall()
        
        return [dict(row) for row in rows]


async def get_payment(payment_id: int) -> Optional[Dict[str, Any]]:
    """
    获取充值申请详情
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE payment_id = ?",
            (payment_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def approve_payment(payment_id: int, admin_uid: int) -> bool:
    """
    批准充值申请
    """
    payment = await get_payment(payment_id)
    if not payment or payment["status"] != "pending":
        return False
    
    vip_duration = await get_vip_duration()
    await set_user_vip(payment["uid"], vip_duration)
    
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            UPDATE payments SET status = 'confirmed', reviewed_at = ?, admin_notes = ?
            WHERE payment_id = ?
            """,
            (datetime.now().isoformat(), f"Approved by admin {admin_uid}", payment_id)
        )
        await db.commit()
    
    return True


async def reject_payment(payment_id: int, admin_uid: int, reason: str = None) -> bool:
    """
    拒绝充值申请
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            UPDATE payments SET status = 'rejected', reviewed_at = ?, admin_notes = ?
            WHERE payment_id = ?
            """,
            (datetime.now().isoformat(), reason or f"Rejected by admin {admin_uid}", payment_id)
        )
        await db.commit()
    
    return True


async def get_all_users_count() -> int:
    """获取所有用户数量"""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_vip_users_count() -> int:
    """获取 VIP 用户数量"""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE is_vip = 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_all_users() -> List[int]:
    """获取所有用户 UID"""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute("SELECT uid FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def get_vip_users() -> List[Dict[str, Any]]:
    """获取所有 VIP 用户"""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT uid, vip_expire_at FROM users WHERE is_vip = 1 ORDER BY vip_expire_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_user_rank(uid: int) -> Optional[int]:
    """
    获取用户注册排名（用于判断是否是前50名）
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute(
            """
            SELECT rank FROM (
                SELECT uid, ROW_NUMBER() OVER (ORDER BY created_at, uid) as rank
                FROM users
            ) WHERE uid = ?
            """,
            (uid,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_free_vip_given_count() -> int:
    """获取已赠送免费VIP的数量"""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute(
            "SELECT given_count FROM free_vip_given WHERE id = 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def increment_free_vip_count() -> None:
    """增加免费VIP赠送计数"""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "UPDATE free_vip_given SET given_count = given_count + 1 WHERE id = 1"
        )
        await db.commit()


async def try_give_free_vip(uid: int) -> bool:
    """
    尝试为新用户赠送免费 VIP（前50名）
    
    Returns:
        是否赠送成功
    """
    count = await get_free_vip_given_count()
    if count >= FREE_VIP_USERS_LIMIT:
        return False
    
    rank = await get_user_rank(uid)
    if rank is None or rank > FREE_VIP_USERS_LIMIT:
        return False
    
    await set_user_vip(uid, FREE_VIP_DURATION_DAYS, "Free VIP for early user")
    await increment_free_vip_count()
    return True


async def get_user_language(uid: int) -> str:
    """
    获取用户语言设置
    
    Args:
        uid: 用户 ID
    
    Returns:
        语言代码 (zh/en)
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute(
            "SELECT language FROM users WHERE uid = ?",
            (uid,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else "zh"


async def set_user_language(uid: int, language: str) -> None:
    """
    设置用户语言
    
    Args:
        uid: 用户 ID
        language: 语言代码 (zh/en)
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "UPDATE users SET language = ? WHERE uid = ?",
            (language, uid)
        )
        await db.commit()


if __name__ == "__main__":
    async def main():
        # 初始化数据库和表
        print("初始化数据库...")
        await init_db()
        print("数据库初始化完成")
        
        # 添加测试用户
        print("\n添加测试用户...")
        await add_user(12345)
        await add_user(67890)
        print("用户添加完成")
        
        # 添加测试订阅
        print("\n添加测试订阅...")
        sub1 = await add_subscription(
            uid=12345,
            exchange="OKX",
            symbol="BTC/USDT",
            timeframe="15m",
            indicator="BB",
            params={"period": 20, "std_dev": 2}
        )
        sub2 = await add_subscription(
            uid=12345,
            exchange="OKX",
            symbol="ETH/USDT",
            timeframe="1h",
            indicator="RSI",
            params={"period": 14}
        )
        sub3 = await add_subscription(
            uid=67890,
            exchange="Binance",
            symbol="BTC/USDT",
            timeframe="5m",
            indicator="MACD",
            params={"fast": 12, "slow": 26, "signal": 9}
        )
        print(f"添加了 3 条订阅记录: sub_id = {sub1}, {sub2}, {sub3}")
        
        # 查询活跃订阅
        print("\n查询活跃订阅...")
        active_subs = await get_active_subs()
        
        print("\n===== 活跃订阅列表 (按 exchange:symbol 归类) =====")
        for key, subs in active_subs.items():
            print(f"\n{key}:")
            for sub in subs:
                print(f"  - sub_id: {sub['sub_id']}, uid: {sub['uid']}, "
                      f"timeframe: {sub['timeframe']}, indicator: {sub['indicator']}, "
                      f"params: {sub['params']}")
        
        print("\n测试完成!")
    
    asyncio.run(main())
