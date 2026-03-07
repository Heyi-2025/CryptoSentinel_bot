"""
行情数据生产模块
负责从交易所抓取 K 线数据，计算技术指标，并写入缓存文件
"""
import asyncio
import json
import os
from typing import Dict, Any, List, Optional

import ccxt.async_support as ccxt
import pandas as pd


CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cryptosentinel_cache.json")

# 全局文件锁，防止并发读写冲突
_cache_lock = asyncio.Lock()

# 请求超时配置（秒）
REQUEST_TIMEOUT = 10

# 最大重试次数
MAX_RETRIES = 3

# 基础休眠时间（秒）
BASE_SLEEP = 1


def calculate_ema(series: pd.Series, length: int) -> pd.Series:
    """
    计算指数移动平均线 (EMA)
    """
    return series.ewm(span=length, adjust=False).mean()


def calculate_bbands(series: pd.Series, length: int = 20, std: float = 2) -> dict:
    """
    计算布林带 (Bollinger Bands)
    """
    middle = series.rolling(window=length).mean()
    std_dev = series.rolling(window=length).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    return {"upper": upper, "middle": middle, "lower": lower}


async def fetch_and_calc(
    exchange_name: str,
    symbol: str,
    timeframe: str,
    retry_count: int = 0
) -> Optional[Dict[str, Any]]:
    """
    抓取指定交易所的最新 200 根 K 线，计算技术指标，返回最新一行的指标数据
    
    Args:
        exchange_name: 交易所名称
        symbol: 交易对
        timeframe: 时间周期
        retry_count: 当前重试次数
    
    Returns:
        包含最新指标数据的字典，失败时返回 None
    """
    df = None
    exchange = None
    
    try:
        exchange_class = getattr(ccxt, exchange_name.lower())
        exchange = exchange_class({
            "enableRateLimit": True,
            "timeout": REQUEST_TIMEOUT * 1000,
        })
        
        ohlcv = await exchange.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=200
        )
        
        if not ohlcv or len(ohlcv) < 50:
            print(f"[警告] {exchange_name} {symbol} 数据不足，跳过")
            return None
        
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        
        close_series = df["close"]
        
        bbands = calculate_bbands(close_series, length=20, std=2)
        df["BBL_20_2"] = bbands["lower"]
        df["BBM_20_2"] = bbands["middle"]
        df["BBU_20_2"] = bbands["upper"]
        
        df["EMA_144"] = calculate_ema(close_series, length=144)
        df["EMA_169"] = calculate_ema(close_series, length=169)
        
        latest = df.iloc[-1]
        
        result = {
            "exchange": exchange_name,
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": int(latest["timestamp"]),
            "open": float(latest["open"]),
            "high": float(latest["high"]),
            "low": float(latest["low"]),
            "close": float(latest["close"]),
            "volume": float(latest["volume"]),
            "BBL_20_2": float(latest["BBL_20_2"]) if pd.notna(latest.get("BBL_20_2")) else None,
            "BBM_20_2": float(latest["BBM_20_2"]) if pd.notna(latest.get("BBM_20_2")) else None,
            "BBU_20_2": float(latest["BBU_20_2"]) if pd.notna(latest.get("BBU_20_2")) else None,
            "EMA_144": float(latest["EMA_144"]) if pd.notna(latest.get("EMA_144")) else None,
            "EMA_169": float(latest["EMA_169"]) if pd.notna(latest.get("EMA_169")) else None,
        }
        
        print(f"[{exchange_name}] {symbol} {timeframe} 指标计算完成")
        return result
        
    except ccxt.DDoSProtection as e:
        print(f"[DDoS] {exchange_name} {symbol} {timeframe}: {e}")
    except ccxt.RateLimitExceeded as e:
        print(f"[限流] {exchange_name} {symbol} {timeframe}: {e}")
    except ccxt.ExchangeNotAvailable as e:
        print(f"[不可用] {exchange_name} {symbol} {timeframe}: {e}")
    except ccxt.RequestTimeout as e:
        print(f"[超时] {exchange_name} {symbol} {timeframe}: {e}")
    except ccxt.NetworkError as e:
        print(f"[网络错误] {exchange_name} {symbol} {timeframe}: {e}")
    except Exception as e:
        print(f"[异常] {exchange_name} {symbol} {timeframe}: {e}")
    
    finally:
        if df is not None:
            del df
        if exchange is not None:
            await exchange.close()
    
    if retry_count < MAX_RETRIES:
        sleep_time = BASE_SLEEP * (2 ** retry_count)
        print(f"[重试] {exchange_name} {symbol} {timeframe}, 等待 {sleep_time}s...")
        await asyncio.sleep(sleep_time)
        return await fetch_and_calc(exchange_name, symbol, timeframe, retry_count + 1)
    
    print(f"[放弃] {exchange_name} {symbol} {timeframe} 达到最大重试次数")
    return None


async def load_existing_cache() -> Dict[str, Any]:
    """
    读取现有缓存数据（带锁）
    """
    if not os.path.exists(CACHE_FILE):
        return {}
    
    async with _cache_lock:
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, ValueError):
            return {}


async def write_cache_atomic(data: Dict[str, Any]) -> None:
    """
    原子写入缓存文件（带锁，增量更新）
    """
    async with _cache_lock:
        existing = {}
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, IOError, ValueError):
                existing = {}
        
        merged = {**existing, **data}
        
        temp_file = CACHE_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
        os.rename(temp_file, CACHE_FILE)


async def run_engine(subs_list: List[Dict[str, Any]]) -> None:
    """
    主循环调度函数
    """
    seen = set()
    unique_subs = []
    for sub in subs_list:
        key = f"{sub['exchange']}:{sub['symbol']}:{sub['timeframe']}"
        if key not in seen:
            seen.add(key)
            unique_subs.append(sub)
    
    print(f"[引擎启动] 共 {len(unique_subs)} 个唯一标的待抓取")
    
    market_data: Dict[str, Any] = {}
    failed_count = 0
    
    for sub in unique_subs:
        exchange_name = sub["exchange"]
        symbol = sub["symbol"]
        timeframe = sub["timeframe"]
        
        print(f">>> 抓取 {exchange_name} {symbol} {timeframe} ...")
        
        result = await fetch_and_calc(exchange_name, symbol, timeframe)
        
        if result is not None:
            cache_key = f"{exchange_name}:{symbol}"
            market_data[cache_key] = result
        else:
            failed_count += 1
        
        await asyncio.sleep(BASE_SLEEP)
    
    # 使用原子写入
    await write_cache_atomic(market_data)
    
    success_count = len(unique_subs) - failed_count
    print(f"[引擎完成] 成功 {success_count}/{len(unique_subs)}, 缓存已写入 {CACHE_FILE}")


if __name__ == "__main__":
    async def main():
        test_subs = [
            {"exchange": "okx", "symbol": "BTC/USDT", "timeframe": "15m"},
            {"exchange": "binance", "symbol": "ETH/USDT", "timeframe": "1h"},
            {"exchange": "okx", "symbol": "SOL/USDT", "timeframe": "5m"},
        ]
        
        await run_engine(test_subs)
    
    asyncio.run(main())
