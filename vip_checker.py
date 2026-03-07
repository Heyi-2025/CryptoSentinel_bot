"""
VIP 到期检测和提醒模块
每小时检查一次 VIP 状态，发送到期提醒
"""
import asyncio
import os
from datetime import datetime, timedelta
from telegram import Bot
from telegram.error import TelegramError

from db_manager import (
    check_and_update_vip_status,
    get_expiring_vip_users,
    get_vip_price,
    get_vip_duration,
    get_deposit_address,
    ADMIN_UID
)


async def get_bot() -> Bot:
    """
    获取 Bot 实例
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise ValueError("未设置 TELEGRAM_BOT_TOKEN 环境变量")
    return Bot(token=token)


async def send_vip_reminder(uid: int, days_left: int) -> bool:
    """
    发送 VIP 到期提醒
    
    Args:
        uid: 用户 ID
        days_left: 剩余天数
    
    Returns:
        是否发送成功
    """
    try:
        bot = await get_bot()
        vip_price = await get_vip_price()
        vip_duration = await get_vip_duration()
        deposit_address = await get_deposit_address()
        
        text = (
            f"⏰ VIP 即将到期提醒\n\n"
            f"您的 VIP 会员将在 {days_left} 天后到期\n\n"
            f"💎 续费价格：{vip_price} USDT / {vip_duration} 天\n\n"
            f"📍 充值地址 (TRC20)：\n"
            f"<code>{deposit_address}</code>\n\n"
            f"转账后发送 /deposit 交易哈希 提交申请"
        )
        
        await bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
        return True
    
    except TelegramError as e:
        print(f"[VIP提醒] 发送失败 UID:{uid}: {e}")
        return False
    except Exception as e:
        print(f"[VIP提醒] 异常 UID:{uid}: {e}")
        return False


async def send_expired_notification(uid: int) -> bool:
    """
    发送 VIP 已过期通知
    """
    try:
        bot = await get_bot()
        vip_price = await get_vip_price()
        vip_duration = await get_vip_duration()
        deposit_address = await get_deposit_address()
        
        text = (
            f"❌ VIP 已过期\n\n"
            f"您的 VIP 会员已过期，已自动降级为普通用户\n"
            f"指标配额已恢复为 1 个\n\n"
            f"💎 重新开通：{vip_price} USDT / {vip_duration} 天\n\n"
            f"📍 充值地址 (TRC20)：\n"
            f"<code>{deposit_address}</code>\n\n"
            f"转账后发送 /deposit 交易哈希 提交申请"
        )
        
        await bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
        return True
    
    except TelegramError as e:
        print(f"[过期通知] 发送失败 UID:{uid}: {e}")
        return False
    except Exception as e:
        print(f"[过期通知] 异常 UID:{uid}: {e}")
        return False


async def check_vip_expiry() -> None:
    """
    检查 VIP 到期情况
    """
    now = datetime.now()
    print(f"[VIP检查] {now.strftime('%Y-%m-%d %H:%M:%S')} 开始检查...")
    
    users_7_days = await get_expiring_vip_users(7)
    for user in users_7_days:
        expire_at = datetime.fromisoformat(user['vip_expire_at'])
        days_left = (expire_at - now).days
        
        if days_left == 7:
            await send_vip_reminder(user['uid'], 7)
            print(f"[VIP提醒] UID:{user['uid']} 还有 7 天到期")
    
    users_3_days = await get_expiring_vip_users(3)
    for user in users_3_days:
        expire_at = datetime.fromisoformat(user['vip_expire_at'])
        days_left = (expire_at - now).days
        
        if days_left == 3:
            await send_vip_reminder(user['uid'], 3)
            print(f"[VIP提醒] UID:{user['uid']} 还有 3 天到期")
    
    expired_uids = await check_and_update_vip_status()
    for uid in expired_uids:
        await send_expired_notification(uid)
        print(f"[VIP过期] UID:{uid} VIP 已过期")
    
    if expired_uids:
        print(f"[VIP检查] 本轮过期 {len(expired_uids)} 个用户")
    else:
        print("[VIP检查] 本轮无用户过期")


async def vip_checker_loop() -> None:
    """
    VIP 检查主循环（每小时检查一次）
    """
    print("[VIP检查器] 启动...")
    
    while True:
        try:
            await check_vip_expiry()
        except Exception as e:
            print(f"[VIP检查器] 异常: {e}")
        
        await asyncio.sleep(3600)


async def main() -> None:
    """
    启动入口
    """
    await vip_checker_loop()


if __name__ == "__main__":
    asyncio.run(main())