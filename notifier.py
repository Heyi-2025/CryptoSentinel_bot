"""
信号调度消费者模块
负责监控行情缓存，比对订阅规则，触发信号后推入队列并发送给用户
"""
import asyncio
import json
import os
from typing import Dict, Any, List, Optional

from telegram import Bot
from telegram.error import TelegramError, RetryAfter, TimedOut

from db_manager import get_active_subs


CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cryptosentinel_cache.json")

# 异步消息队列
message_queue: asyncio.Queue = asyncio.Queue()

# 文件读取锁
_cache_lock = asyncio.Lock()

# 信号状态缓存：记录每个订阅上次触发状态，避免重复触发
# 结构: {sub_id: {"timestamp": int, "bb_triggered": bool, "vegas_triggered": bool}}
_signal_state: Dict[int, Dict[str, Any]] = {}

# Telegram Bot 实例
_bot_instance: Optional[Bot] = None


async def get_bot() -> Bot:
    """
    获取 Bot 实例（单例）
    """
    global _bot_instance
    if _bot_instance is None:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise ValueError("未设置 TELEGRAM_BOT_TOKEN 环境变量")
        _bot_instance = Bot(token=token)
    return _bot_instance


async def send_telegram_message(uid: int, msg: str, retry_count: int = 0) -> bool:
    """
    发送真实的 Telegram 消息
    
    Args:
        uid: 用户 ID
        msg: 消息内容
        retry_count: 当前重试次数
    
    Returns:
        是否发送成功
    """
    try:
        bot = await get_bot()
        await bot.send_message(chat_id=uid, text=msg, parse_mode="HTML")
        return True
    
    except RetryAfter as e:
        if retry_count < 3:
            retry_after = e.retry_after if isinstance(e.retry_after, (int, float)) else e.retry_after.total_seconds()
            print(f"[TG限流] 等待 {retry_after} 秒后重试...")
            await asyncio.sleep(retry_after)
            return await send_telegram_message(uid, msg, retry_count + 1)
        print(f"[TG限流] 达到最大重试次数")
        return False
    
    except TimedOut:
        if retry_count < 3:
            print(f"[TG超时] 重试 {retry_count + 1}/3...")
            await asyncio.sleep(2)
            return await send_telegram_message(uid, msg, retry_count + 1)
        print(f"[TG超时] 达到最大重试次数")
        return False
    
    except TelegramError as e:
        print(f"[TG错误] 用户 {uid}: {e}")
        return False
    
    except Exception as e:
        print(f"[TG异常] 用户 {uid}: {e}")
        return False


async def mock_send_tg(uid: int, msg: str) -> bool:
    """
    模拟发送 Telegram 消息
    """
    print(f"[TG Mock] 发送给用户 {uid}: {msg}")
    await asyncio.sleep(0.1)
    return True


async def load_market_cache() -> Dict[str, Any]:
    """
    读取本地行情缓存文件（带锁）
    """
    if not os.path.exists(CACHE_FILE):
        return {}
    
    async with _cache_lock:
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, ValueError):
            return {}


def check_bb_signal_change(
    market_data: Dict[str, Any], 
    prev_state: Optional[Dict[str, Any]]
) -> Optional[bool]:
    """
    检查 BB 突破状态变化（影线触碰布林上轨）
    
    Returns:
        True: 新触发突破（之前未突破，现在突破）
        False: 突破消失（之前突破，现在未突破）
        None: 状态未变化或数据不足
    """
    high = market_data.get("high")
    bbu = market_data.get("BBU_20_2")
    
    if high is None or bbu is None:
        return None
    
    current_triggered = high > bbu
    prev_triggered = prev_state.get("bb_triggered", False) if prev_state else False
    
    if current_triggered and not prev_triggered:
        return True
    elif not current_triggered and prev_triggered:
        return False
    return None


def check_vegas_signal_change(
    market_data: Dict[str, Any], 
    prev_state: Optional[Dict[str, Any]]
) -> List[str]:
    """
    检查 VEGAS 触碰信号
    
    Returns:
        信号列表，每个元素是一个信号类型：
        "cross_up_144": K线上穿EMA144 (收盘价从下向上穿过)
        "cross_down_144": K线下穿EMA144 (收盘价从上向下穿过)
        "cross_up_169": K线上穿EMA169
        "cross_down_169": K线下穿EMA169
    """
    high = market_data.get("high")
    low = market_data.get("low")
    close = market_data.get("close")
    ema_144 = market_data.get("EMA_144")
    ema_169 = market_data.get("EMA_169")
    
    if high is None or low is None or close is None or ema_144 is None or ema_169 is None:
        return []
    
    signals = []
    
    prev_cross_up_144 = prev_state.get("cross_up_144", False) if prev_state else False
    prev_cross_down_144 = prev_state.get("cross_down_144", False) if prev_state else False
    prev_cross_up_169 = prev_state.get("cross_up_169", False) if prev_state else False
    prev_cross_down_169 = prev_state.get("cross_down_169", False) if prev_state else False
    
    cross_up_144 = low < ema_144 < high and close > ema_144
    cross_down_144 = low < ema_144 < high and close < ema_144
    
    cross_up_169 = low < ema_169 < high and close > ema_169
    cross_down_169 = low < ema_169 < high and close < ema_169
    
    if cross_up_144 and not prev_cross_up_144:
        signals.append("cross_up_144")
    
    if cross_down_144 and not prev_cross_down_144:
        signals.append("cross_down_144")
    
    if cross_up_169 and not prev_cross_up_169:
        signals.append("cross_up_169")
    
    if cross_down_169 and not prev_cross_down_169:
        signals.append("cross_down_169")
    
    return signals


def check_ma_density_signal(
    market_data: Dict[str, Any], 
    prev_state: Optional[Dict[str, Any]]
) -> Optional[str]:
    """
    检查均线密集信号
    
    密集级别:
        0 = 无密集
        1 = 核心密集 (MA20/EMA20/MA60/EMA60 收敛)
        2 = 全员密集 (上述4条 + MA120/EMA120 全部收敛)
    
    只在升级时触发通知:
        0→1: 核心密集 🟠
        0→2 或 1→2: 全员密集 🟢
    
    Returns:
        信号消息文本，无升级信号返回 None
    """
    ma_20 = market_data.get("MA_20")
    ema_20 = market_data.get("EMA_20")
    ma_60 = market_data.get("MA_60")
    ema_60 = market_data.get("EMA_60")
    ma_120 = market_data.get("MA_120")
    ema_120 = market_data.get("EMA_120")
    atr = market_data.get("ATR_14")
    
    if any(v is None for v in [ma_20, ema_20, ma_60, ema_60, atr]):
        return None
    
    core_top = max(ma_20, ema_20, ma_60, ema_60)
    core_bot = min(ma_20, ema_20, ma_60, ema_60)
    core_width = core_top - core_bot
    
    is_core_dense = core_width < (atr * 0.7)
    
    is_all_dense = False
    if is_core_dense and ma_120 is not None and ema_120 is not None:
        core_center = (core_top + core_bot) / 2
        dist_120_max = max(abs(ma_120 - core_center), abs(ema_120 - core_center))
        is_all_dense = dist_120_max < (atr * 0.8)
    
    current_level = 0
    if is_all_dense:
        current_level = 2
    elif is_core_dense:
        current_level = 1
    
    prev_level = prev_state.get("ma_density_level", 0) if prev_state else 0
    
    symbol = market_data.get("symbol", "")
    
    if current_level > prev_level:
        if current_level == 2:
            return f"🟢 均线全员密集\n{symbol} 六条均线共振，大行情可能来临\n核心带宽: {core_width:.4f} / ATR: {atr:.4f}"
        elif current_level == 1:
            return f"🟠 均线核心密集\n{symbol} 短期均线组开始收敛，蓄势待发\n带宽: {core_width:.4f} / ATR: {atr:.4f}"
    
    return None


def check_signal(
    market_data: Dict[str, Any], 
    sub: Dict[str, Any],
    prev_state: Optional[Dict[str, Any]]
) -> Optional[str]:
    """
    根据指标类型检查是否触发信号（基于状态变化）
    
    Args:
        market_data: 当前行情数据
        sub: 订阅配置
        prev_state: 上一次的状态
    
    Returns:
        信号消息文本，无信号返回 None
    """
    indicator = sub.get("indicator", "").upper()
    timestamp = market_data.get("timestamp", 0)
    
    if indicator == "BB":
        change = check_bb_signal_change(market_data, prev_state)
        
        if change is None:
            return None
        
        symbol = market_data.get("symbol")
        high = market_data.get("high")
        close = market_data.get("close")
        bbu = market_data.get("BBU_20_2")
        
        if high is None or bbu is None:
            return None
        
        if change:
            close_str = f"\n收盘价: {close:.2f}" if close else ""
            return f"🚀 BB 突破信号\n{symbol} 最高价 {high:.2f} 触碰布林上轨 {bbu:.2f}{close_str}"
        return None
    
    elif indicator == "VEGAS":
        signals = check_vegas_signal_change(market_data, prev_state)
        
        if not signals:
            return None
        
        symbol = market_data.get("symbol")
        ema_144 = market_data.get("EMA_144")
        ema_169 = market_data.get("EMA_169")
        
        if ema_144 is None or ema_169 is None:
            return None
        
        msg_parts = []
        for signal_type in signals:
            if signal_type == "cross_up_144":
                msg_parts.append(f"⬆️ {symbol} K线上穿 EMA144 ({ema_144:.2f})")
            elif signal_type == "cross_down_144":
                msg_parts.append(f"⬇️ {symbol} K线下穿 EMA144 ({ema_144:.2f})")
            elif signal_type == "cross_up_169":
                msg_parts.append(f"⬆️ {symbol} K线上穿 EMA169 ({ema_169:.2f})")
            elif signal_type == "cross_down_169":
                msg_parts.append(f"⬇️ {symbol} K线下穿 EMA169 ({ema_169:.2f})")
        
        if msg_parts:
            return "📈 VEGAS 触碰信号\n" + "\n".join(msg_parts)
        
        return None
    
    elif indicator == "MA_DENSITY":
        return check_ma_density_signal(market_data, prev_state)
    
    return None


def update_signal_state(
    sub_id: int, 
    market_data: Dict[str, Any], 
    indicator: str
) -> None:
    """
    更新信号状态缓存
    """
    timestamp = market_data.get("timestamp", 0)
    
    bb_triggered = None
    cross_up_144 = None
    cross_down_144 = None
    cross_up_169 = None
    cross_down_169 = None
    ma_density_level = 0
    
    high = market_data.get("high")
    bbu = market_data.get("BBU_20_2")
    low = market_data.get("low")
    close = market_data.get("close")
    ema_144 = market_data.get("EMA_144")
    ema_169 = market_data.get("EMA_169")
    
    if high is not None and bbu is not None:
        bb_triggered = high > bbu
    
    if high is not None and low is not None and close is not None:
        if ema_144 is not None:
            cross_up_144 = low < ema_144 < high and close > ema_144
            cross_down_144 = low < ema_144 < high and close < ema_144
        if ema_169 is not None:
            cross_up_169 = low < ema_169 < high and close > ema_169
            cross_down_169 = low < ema_169 < high and close < ema_169
    
    ma_20 = market_data.get("MA_20")
    ema_20 = market_data.get("EMA_20")
    ma_60 = market_data.get("MA_60")
    ema_60 = market_data.get("EMA_60")
    ma_120 = market_data.get("MA_120")
    ema_120 = market_data.get("EMA_120")
    atr = market_data.get("ATR_14")
    
    if all(v is not None for v in [ma_20, ema_20, ma_60, ema_60, atr]):
        core_top = max(ma_20, ema_20, ma_60, ema_60)
        core_bot = min(ma_20, ema_20, ma_60, ema_60)
        core_width = core_top - core_bot
        
        is_core_dense = core_width < (atr * 0.7)
        is_all_dense = False
        
        if is_core_dense and ma_120 is not None and ema_120 is not None:
            core_center = (core_top + core_bot) / 2
            dist_120_max = max(abs(ma_120 - core_center), abs(ema_120 - core_center))
            is_all_dense = dist_120_max < (atr * 0.8)
        
        if is_all_dense:
            ma_density_level = 2
        elif is_core_dense:
            ma_density_level = 1
    
    _signal_state[sub_id] = {
        "timestamp": timestamp,
        "bb_triggered": bb_triggered if bb_triggered is not None else False,
        "cross_up_144": cross_up_144 if cross_up_144 is not None else False,
        "cross_down_144": cross_down_144 if cross_down_144 is not None else False,
        "cross_up_169": cross_up_169 if cross_up_169 is not None else False,
        "cross_down_169": cross_down_169 if cross_down_169 is not None else False,
        "ma_density_level": ma_density_level
    }


async def watch_and_notify() -> None:
    """
    主监控循环
    """
    print("[监控启动] 开始监控行情信号...")
    
    while True:
        try:
            market_data_dict = await load_market_cache()
            
            if not market_data_dict:
                await asyncio.sleep(5)
                continue
            
            subs_by_key = await get_active_subs()
            
            if not subs_by_key:
                await asyncio.sleep(5)
                continue
            
            triggered_count = 0
            for cache_key, subs_list in subs_by_key.items():
                market_data = market_data_dict.get(cache_key)
                
                if market_data is None:
                    continue
                
                current_timestamp = market_data.get("timestamp", 0)
                
                for sub in subs_list:
                    try:
                        sub_id = sub["sub_id"]
                        indicator = sub.get("indicator", "BB")
                        
                        prev_state = _signal_state.get(sub_id)
                        prev_timestamp = prev_state.get("timestamp", 0) if prev_state else 0
                        
                        if current_timestamp == prev_timestamp:
                            continue
                        
                        signal_msg = check_signal(market_data, sub, prev_state)
                        
                        update_signal_state(sub_id, market_data, indicator)
                        
                        if signal_msg:
                            uid = sub["uid"]
                            
                            await message_queue.put({
                                "uid": uid,
                                "msg": signal_msg,
                                "sub_id": sub_id
                            })
                            triggered_count += 1
                            print(f"[触发] UID:{uid} {signal_msg}")
                    except Exception as e:
                        print(f"[检查信号异常] sub_id={sub.get('sub_id')}: {e}")
            
            if triggered_count > 0:
                print(f"[监控] 本轮触发 {triggered_count} 条信号")
                
        except Exception as e:
            print(f"[监控异常] {e}")
        
        await asyncio.sleep(5)


async def send_worker() -> None:
    """
    消费队列的工作函数
    """
    print("[Worker] 消息消费 worker 已启动...")
    
    while True:
        try:
            item = await message_queue.get()
            
            uid = item["uid"]
            msg = item["msg"]
            
            success = await send_telegram_message(uid, msg)
            
            if success:
                print(f"[Worker] 消息发送成功 -> UID:{uid}")
            else:
                print(f"[Worker] 消息发送失败 -> UID:{uid}")
            
            message_queue.task_done()
            
        except Exception as e:
            print(f"[Worker] 异常: {e}")


async def main() -> None:
    """
    启动入口
    """
    worker_task = asyncio.create_task(send_worker())
    await watch_and_notify()


if __name__ == "__main__":
    asyncio.run(main())
