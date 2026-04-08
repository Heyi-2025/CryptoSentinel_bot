"""
数据库管理模块
负责 SQLite 数据库的异步增删改查操作
"""
import asyncio
import aiosqlite
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DATABASE_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cryptosentinel.db")

ADMIN_UID = int(os.environ.get("ADMIN_UID", "0"))

DONATE_ADDRESS = os.environ.get("DONATE_ADDRESS", "")

MAX_SUBSCRIPTIONS = 10


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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        
        await db.commit()


async def add_user(uid: int) -> None:
    """
    插入新用户，如果用户已存在则忽略
    
    Args:
        uid: 用户 ID
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (uid) VALUES (?)",
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
        indicator: 指标名称 (如 BB, VEGAS)
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


async def get_all_users_count() -> int:
    """获取所有用户数量"""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_all_users() -> List[int]:
    """获取所有用户 UID"""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute("SELECT uid FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


if __name__ == "__main__":
    async def main():
        print("初始化数据库...")
        await init_db()
        print("数据库初始化完成")
        
        print("\n添加测试用户...")
        await add_user(12345)
        await add_user(67890)
        print("用户添加完成")
        
        print("\n添加测试订阅...")
        sub1 = await add_subscription(
            uid=12345,
            exchange="OKX",
            symbol="BTC/USDT",
            timeframe="15m",
            indicator="BB",
            params={"period": 20, "std_dev": 2}
        )
        print(f"添加了订阅记录: sub_id = {sub1}")
        
        print("\n查询活跃订阅...")
        active_subs = await get_active_subs()
        
        print("\n===== 活跃订阅列表 =====")
        for key, subs in active_subs.items():
            print(f"\n{key}:")
            for sub in subs:
                print(f"  - sub_id: {sub['sub_id']}, uid: {sub['uid']}, "
                      f"timeframe: {sub['timeframe']}, indicator: {sub['indicator']}")
        
        print("\n测试完成!")
    
    asyncio.run(main())