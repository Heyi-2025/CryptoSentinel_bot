"""
Telegram Bot 前端交互模块
使用 python-telegram-bot v20+ 的 Application 和 ConversationHandler
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    JobQueue,
)

from db_manager import (
    add_user, add_subscription, get_user_sub_count, get_user_subs, delete_subscription,
    get_user_info, get_max_subscriptions, try_give_free_vip,
    create_payment_request, get_pending_payments, get_payment,
    approve_payment, reject_payment,
    get_vip_price, get_vip_duration, get_deposit_address,
    get_all_users, get_vip_users, get_all_users_count, get_vip_users_count,
    get_expiring_vip_users, check_and_update_vip_status,
    set_config, ADMIN_UID, get_user_language, set_user_language
)

from i18n import get_message, detect_language, get_button_text


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DEPOSIT_ADDRESS = "TQ66Jy7fgubE9H3dj981gfqnEfodSBVPfx"

SUPPORTED_SYMBOLS_CACHE = {}
SUPPORTED_SYMBOLS_CACHE_TIME = 0
SUPPORTED_SYMBOLS_CACHE_TTL = 3600

(
    EXCHANGE,
    SYMBOL,
    TIMEFRAME,
    INDICATOR,
    CONFIRM,
    DEPOSIT_TX_HASH,
    BROADCAST_MESSAGE,
) = range(7)

CONVERSATION_TIMEOUT = 120


async def fetch_okx_symbols() -> set:
    """
    从 OKX API 获取支持的交易对列表
    """
    import ccxt.async_support as ccxt
    
    try:
        exchange = ccxt.okx({"enableRateLimit": True})
        markets = await exchange.fetch_markets()
        await exchange.close()
        
        symbols = set()
        for market in markets:
            symbol = market.get("symbol")
            if symbol and "/USDT" in symbol:
                symbols.add(symbol)
        
        return symbols
    except Exception as e:
        logger.error(f"获取 OKX 交易对失败: {e}")
        return set()


async def get_supported_symbols() -> set:
    """
    获取支持的交易对列表（带缓存）
    """
    import time
    
    global SUPPORTED_SYMBOLS_CACHE, SUPPORTED_SYMBOLS_CACHE_TIME
    
    current_time = time.time()
    
    if SUPPORTED_SYMBOLS_CACHE and (current_time - SUPPORTED_SYMBOLS_CACHE_TIME) < SUPPORTED_SYMBOLS_CACHE_TTL:
        return SUPPORTED_SYMBOLS_CACHE
    
    symbols = await fetch_okx_symbols()
    
    if symbols:
        SUPPORTED_SYMBOLS_CACHE = symbols
        SUPPORTED_SYMBOLS_CACHE_TIME = current_time
    
    return SUPPORTED_SYMBOLS_CACHE


async def get_lang(update: Update) -> str:
    """
    获取用户的语言设置
    """
    if not update.effective_user:
        return "zh"
    
    uid = update.effective_user.id
    
    lang = await get_user_language(uid)
    if lang:
        return lang
    
    lang_code = update.effective_user.language_code
    return detect_language(lang_code)


async def safe_reply(update: Update, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> None:
    """
    安全发送消息，自动处理 update 来源
    """
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)


async def safe_edit(update: Update, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> None:
    """
    安全编辑消息
    """
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        except Exception:
            pass


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    全局错误处理回调
    """
    logger.error(f"处理更新时发生错误: {context.error}")
    
    try:
        lang = await get_lang(update) if update else "zh"
        await safe_reply(update, get_message("error_timeout", lang))
    except Exception:
        pass


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    /start 命令入口，检查门票并引导进入状态机
    """
    try:
        if not update.effective_user:
            return ConversationHandler.END
        
        uid = update.effective_user.id
        lang = await get_lang(update)
        
        await add_user(uid)
        await try_give_free_vip(uid)
        
        max_subs = await get_max_subscriptions(uid)
        sub_count = await get_user_sub_count(uid)
        
        if sub_count >= max_subs:
            await safe_reply(
                update,
                get_message("max_subs_reached", lang, max=max_subs)
            )
            return ConversationHandler.END
        
        keyboard = [
            [
                InlineKeyboardButton("Binance", callback_data="Binance"),
                InlineKeyboardButton("OKX", callback_data="OKX"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_reply(
            update,
            get_message("welcome", lang),
            reply_markup=reply_markup
        )
        
        return EXCHANGE
        
    except Exception as e:
        logger.error(f"start 命令异常: {e}")
        return ConversationHandler.END


async def exchange_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    State 1: 处理交易所选择
    """
    try:
        query = update.callback_query
        if not query:
            return ConversationHandler.END
        
        await query.answer()
        
        exchange = query.data
        context.user_data["exchange"] = exchange
        
        lang = await get_lang(update)
        await safe_edit(
            update,
            get_message("exchange_selected", lang, exchange=exchange)
        )
        
        return SYMBOL
        
    except Exception as e:
        logger.error(f"exchange_callback 异常: {e}")
        return ConversationHandler.END


async def symbol_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    State 2: 处理交易对输入
    """
    try:
        if not update.message:
            return ConversationHandler.END
        
        lang = await get_lang(update)
        symbol = update.message.text.strip().upper()
        
        if not symbol or "/" not in symbol or len(symbol) > 20:
            await update.message.reply_text(get_message("symbol_format_error", lang))
            return SYMBOL
        
        parts = symbol.split("/")
        if len(parts) != 2:
            await update.message.reply_text(get_message("symbol_format_error", lang))
            return SYMBOL
        
        base, quote = parts
        if not base or not quote:
            await update.message.reply_text(get_message("symbol_format_error", lang))
            return SYMBOL
        
        valid_quotes = {"USDT", "USDC", "BUSD", "USD"}
        if quote not in valid_quotes:
            await update.message.reply_text(
                get_message("symbol_quote_warning", lang, quote=quote, valid_quotes=', '.join(valid_quotes))
            )
        
        supported_symbols = await get_supported_symbols()
        
        if supported_symbols and symbol not in supported_symbols:
            popular_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", 
                             "ADA/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT", "LINK/USDT"]
            available = [s for s in popular_symbols if s in supported_symbols][:10]
            symbols_str = "\n".join(available) if available else "BTC/USDT, ETH/USDT, SOL/USDT"
            
            await update.message.reply_text(
                get_message("symbol_not_supported", lang, symbols=symbols_str)
            )
            return SYMBOL
        
        context.user_data["symbol"] = symbol
        
        keyboard = [
            [
                InlineKeyboardButton("15m", callback_data="15m"),
                InlineKeyboardButton("1h", callback_data="1h"),
                InlineKeyboardButton("4h", callback_data="4h"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            get_message("symbol_selected", lang, symbol=symbol),
            reply_markup=reply_markup
        )
        
        return TIMEFRAME
        
    except Exception as e:
        logger.error(f"symbol_received 异常: {e}")
        return ConversationHandler.END


async def timeframe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    State 3: 处理时间周期选择
    """
    try:
        query = update.callback_query
        if not query:
            return ConversationHandler.END
        
        await query.answer()
        
        timeframe = query.data
        context.user_data["timeframe"] = timeframe
        
        keyboard = [
            [
                InlineKeyboardButton("BB 布林带", callback_data="BB"),
                InlineKeyboardButton("VEGAS 通道", callback_data="VEGAS"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit(
            update,
            f"✅ 交易对: {context.user_data.get('symbol', 'N/A')}\n"
            f"✅ 时间周期: {timeframe}\n\n请选择技术指标：",
            reply_markup=reply_markup
        )
        
        return INDICATOR
        
    except Exception as e:
        logger.error(f"timeframe_callback 异常: {e}")
        return ConversationHandler.END


async def indicator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    State 4: 处理指标选择，显示确认
    """
    try:
        query = update.callback_query
        if not query:
            return ConversationHandler.END
        
        await query.answer()
        
        indicator = query.data
        context.user_data["indicator"] = indicator
        
        exchange = context.user_data.get("exchange", "N/A")
        symbol = context.user_data.get("symbol", "N/A")
        timeframe = context.user_data.get("timeframe", "N/A")
        
        indicator_name = "BB 布林带" if indicator == "BB" else "VEGAS 通道"
        
        confirm_text = (
            f"📋 确认您的监控配置：\n\n"
            f"• 交易所: {exchange}\n"
            f"• 交易对: {symbol}\n"
            f"• 时间周期: {timeframe}\n"
            f"• 技术指标: {indicator_name}\n\n"
            "请确认是否保存？"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ 确认", callback_data="confirm"),
                InlineKeyboardButton("❌ 取消", callback_data="cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit(update, confirm_text, reply_markup=reply_markup)
        
        return CONFIRM
        
    except Exception as e:
        logger.error(f"indicator_callback 异常: {e}")
        return ConversationHandler.END


async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    State 5: 处理确认，保存到数据库
    """
    try:
        query = update.callback_query
        if not query:
            return ConversationHandler.END
        
        await query.answer()
        
        if query.data == "cancel":
            await safe_edit(update, "❌ 已取消操作")
            return ConversationHandler.END
        
        if not update.effective_user:
            return ConversationHandler.END
        
        uid = update.effective_user.id
        exchange = context.user_data.get("exchange")
        symbol = context.user_data.get("symbol")
        timeframe = context.user_data.get("timeframe")
        indicator = context.user_data.get("indicator")
        
        if not all([exchange, symbol, timeframe, indicator]):
            await safe_edit(update, "❌ 数据不完整，请重新开始 /start")
            return ConversationHandler.END
        
        if indicator == "BB":
            params = {"period": 20, "std_dev": 2}
        else:
            params = {"ema_fast": 144, "ema_slow": 169}
        
        try:
            sub_id = await add_subscription(
                uid=uid,
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                indicator=indicator,
                params=params
            )
            
            await safe_edit(
                update,
                f"✅ 配置已保存！\n\n"
                f"Sub ID: {sub_id}\n"
                f"交易所: {exchange}\n"
                f"交易对: {symbol}\n"
                f"周期: {timeframe}\n"
                f"指标: {indicator}"
            )
        except Exception as db_error:
            logger.error(f"保存订阅失败: {db_error}")
            await safe_edit(update, "❌ 保存失败，请重试")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"confirm_callback 异常: {e}")
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    取消对话
    """
    await safe_reply(update, "❌ 操作已取消")
    return ConversationHandler.END


async def list_subs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /list 命令：查看当前用户的订阅列表
    """
    try:
        if not update.effective_user:
            return
        
        uid = update.effective_user.id
        subs = await get_user_subs(uid)
        
        if not subs:
            await safe_reply(update, "📭 您当前没有任何监控任务\n\n发送 /start 添加新监控")
            return
        
        text = "📋 您的监控任务列表：\n\n"
        for sub in subs:
            status = "✅" if sub["is_active"] else "❌"
            text += (
                f"{status} #{sub['sub_id']} {sub['exchange']} {sub['symbol']}\n"
                f"   周期: {sub['timeframe']} | 指标: {sub['indicator']}\n\n"
            )
        
        text += "💡 使用 /delete [编号] 删除任务"
        await safe_reply(update, text)
        
    except Exception as e:
        logger.error(f"list_subs 异常: {e}")
        await safe_reply(update, "❌ 查询失败，请重试")


async def delete_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /delete 命令：删除指定订阅
    用法：/delete 123
    """
    try:
        if not update.effective_user:
            return
        
        if not context.args:
            await safe_reply(update, "❌ 请指定要删除的任务编号\n\n用法：/delete 123")
            return
        
        try:
            sub_id = int(context.args[0])
        except ValueError:
            await safe_reply(update, "❌ 编号必须是数字\n\n用法：/delete 123")
            return
        
        uid = update.effective_user.id
        
        # 验证该任务是否属于当前用户
        user_subs = await get_user_subs(uid)
        valid_ids = [s["sub_id"] for s in user_subs]
        
        if sub_id not in valid_ids:
            await safe_reply(update, "❌ 无法删除：该任务不存在或不属于您")
            return
        
        # 执行删除
        success = await delete_subscription(sub_id, uid)
        
        if success:
            await safe_reply(update, f"✅ 已删除监控任务 #{sub_id}")
        else:
            await safe_reply(update, "❌ 删除失败，请重试")
            
    except Exception as e:
        logger.error(f"delete_sub 异常: {e}")
        await safe_reply(update, "❌ 操作失败，请重试")


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /myid 命令：查看自己的用户 ID
    """
    if not update.effective_user:
        return
    
    lang = await get_lang(update)
    uid = update.effective_user.id
    username = update.effective_user.username or ("未设置" if lang == "zh" else "Not set")
    
    await safe_reply(
        update,
        get_message("myid", lang, uid=uid, username=username)
    )


async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /vip 命令：查看 VIP 说明和充值
    """
    if not update.effective_user:
        return
    
    lang = await get_lang(update)
    uid = update.effective_user.id
    user_info = await get_user_info(uid)
    
    vip_price = await get_vip_price()
    vip_duration = await get_vip_duration()
    deposit_address = await get_deposit_address()
    
    is_vip = user_info and user_info.get("is_vip")
    vip_expire = user_info.get("vip_expire_at") if user_info else None
    
    if is_vip and vip_expire:
        expire_date = datetime.fromisoformat(vip_expire).strftime("%Y-%m-%d")
        status_text = get_message("vip_status_vip", lang, expire_date=expire_date)
    else:
        status_text = get_message("vip_status_normal", lang)
    
    text = (
        f"{get_message('vip_title', lang)}\n\n"
        f"📋 您的状态：\n{status_text}\n\n"
        f"{get_message('vip_benefits', lang, duration=vip_duration)}\n\n"
        f"{get_message('vip_price', lang, price=vip_price)}\n\n"
        f"{get_message('vip_deposit_address', lang, address=deposit_address)}\n\n"
        f"{get_message('vip_deposit_hint', lang)}"
    )
    
    keyboard = [
        [InlineKeyboardButton(get_button_text("btn_submit_deposit", lang), callback_data="deposit_submit")],
        [InlineKeyboardButton(get_button_text("btn_vip_status", lang), callback_data="vip_status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_reply(update, text, reply_markup)


async def mystatus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /mystatus 命令：查看自己的 VIP 状态
    """
    if not update.effective_user:
        return
    
    lang = await get_lang(update)
    uid = update.effective_user.id
    user_info = await get_user_info(uid)
    
    if not user_info:
        await safe_reply(update, get_message("error_user_not_found", lang))
        return
    
    is_vip = user_info.get("is_vip")
    vip_expire = user_info.get("vip_expire_at")
    created_at = user_info.get("created_at")
    
    sub_count = await get_user_sub_count(uid)
    max_subs = await get_max_subscriptions(uid)
    
    if is_vip and vip_expire:
        expire_date = datetime.fromisoformat(vip_expire)
        days_left = (expire_date - datetime.now()).days
        status_text = get_message("mystatus_vip", lang, 
            expire_date=expire_date.strftime('%Y-%m-%d'), 
            days_left=days_left
        )
    else:
        status_text = get_message("mystatus_normal", lang)
    
    register_date = datetime.fromisoformat(created_at).strftime("%Y-%m-%d") if created_at else ("未知" if lang == "zh" else "Unknown")
    
    text = (
        f"{get_message('mystatus_title', lang)}\n\n"
        f"会员等级：\n{status_text}\n\n"
        f"{get_message('mystatus_quota', lang, current=sub_count, max=max_subs)}\n"
        f"{get_message('mystatus_register_date', lang, date=register_date)}"
    )
    
    keyboard = []
    if not is_vip:
        keyboard.append([InlineKeyboardButton(get_button_text("btn_open_vip", lang), callback_data="open_vip")])
    keyboard.append([InlineKeyboardButton(get_button_text("admin_btn_back", lang), callback_data="back_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await safe_reply(update, text, reply_markup)


async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /deposit 命令：提交充值申请
    用法：/deposit 交易哈希
    """
    if not update.effective_user:
        return
    
    lang = await get_lang(update)
    uid = update.effective_user.id
    
    if not context.args:
        await safe_reply(update, get_message("deposit_missing_hash", lang))
        return
    
    tx_hash = context.args[0].strip()
    
    if len(tx_hash) < 10:
        await safe_reply(update, get_message("deposit_hash_too_short", lang))
        return
    
    if not all(c in '0123456789abcdefABCDEF' for c in tx_hash):
        await safe_reply(update, "❌ 交易哈希格式错误，请输入正确的 TRC20 交易哈希")
        return
    
    payment_id = await create_payment_request(uid, tx_hash)
    
    await safe_reply(
        update,
        get_message("deposit_success", lang, tx_hash=tx_hash[:20], payment_id=payment_id)
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理按钮回调
    """
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    uid = update.effective_user.id
    data = query.data
    lang = await get_lang(update)
    
    if data == "deposit_submit":
        await query.edit_message_text(get_message("deposit_hint", lang))
    
    elif data == "vip_status":
        user_info = await get_user_info(uid)
        if not user_info:
            await query.edit_message_text(get_message("error_user_not_found", lang))
            return
        
        is_vip = user_info.get("is_vip")
        vip_expire = user_info.get("vip_expire_at")
        sub_count = await get_user_sub_count(uid)
        max_subs = await get_max_subscriptions(uid)
        
        if is_vip and vip_expire:
            expire_date = datetime.fromisoformat(vip_expire)
            days_left = (expire_date - datetime.now()).days
            status_text = get_message("mystatus_vip", lang,
                expire_date=expire_date.strftime('%Y-%m-%d'),
                days_left=days_left
            )
        else:
            status_text = get_message("vip_status_normal", lang)
        
        text = (
            f"{get_message('mystatus_title', lang)}\n\n"
            f"{status_text}\n\n"
            f"{get_message('mystatus_quota', lang, current=sub_count, max=max_subs)}"
        )
        
        keyboard = [[InlineKeyboardButton(get_button_text("admin_btn_back", lang), callback_data="back_vip")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "open_vip":
        vip_price = await get_vip_price()
        vip_duration = await get_vip_duration()
        deposit_address = await get_deposit_address()
        
        text = (
            f"{get_message('open_vip_title', lang)}\n\n"
            f"{get_message('open_vip_price', lang, price=vip_price, duration=vip_duration)}\n\n"
            f"{get_message('vip_deposit_address', lang, address=deposit_address)}\n\n"
            f"{get_message('vip_deposit_hint', lang)}"
        )
        
        keyboard = [
            [InlineKeyboardButton(get_button_text("btn_submit_deposit", lang), callback_data="deposit_submit")],
            [InlineKeyboardButton(get_button_text("admin_btn_back", lang), callback_data="back_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "back_vip":
        await vip(update, context)
    
    elif data == "back_main":
        await query.edit_message_text(get_message("welcome", lang))
    
    elif data.startswith("lang_"):
        new_lang = data.split("_")[-1]
        await set_user_language(uid, new_lang)
        await query.edit_message_text(get_message("language_changed", new_lang))


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /language 命令：切换语言
    """
    lang = await get_lang(update)
    
    keyboard = [
        [InlineKeyboardButton(get_button_text("btn_lang_zh", lang), callback_data="lang_zh")],
        [InlineKeyboardButton(get_button_text("btn_lang_en", lang), callback_data="lang_en")],
    ]
    
    await safe_reply(
        update,
        get_message("language_select", lang),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /admin 命令：管理员面板
    """
    if not update.effective_user:
        return
    
    uid = update.effective_user.id
    
    if uid != ADMIN_UID:
        await safe_reply(update, "❌ 您没有权限访问管理员面板")
        return
    
    total_users = await get_all_users_count()
    vip_users = await get_vip_users_count()
    pending_payments = len(await get_pending_payments())
    
    text = (
        f"🔧 管理员控制面板\n\n"
        f"📊 统计：\n"
        f"• 总用户：{total_users}\n"
        f"• VIP 用户：{vip_users}\n"
        f"• 待处理充值：{pending_payments}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("💰 充值申请列表", callback_data="admin_payments")],
        [InlineKeyboardButton("👥 VIP 用户列表", callback_data="admin_vip_list")],
        [InlineKeyboardButton("📢 群发消息", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊 统计信息", callback_data="admin_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_reply(update, text, reply_markup)


async def admin_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理管理员按钮回调
    """
    query = update.callback_query
    if not query:
        return
    
    uid = update.effective_user.id
    
    if uid != ADMIN_UID:
        await query.answer("❌ 无权限", show_alert=True)
        return
    
    await query.answer()
    data = query.data
    
    if data == "admin_payments":
        payments = await get_pending_payments()
        
        if not payments:
            await query.edit_message_text(
                "💰 充值申请列表\n\n暂无待处理的申请",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 返回", callback_data="admin_back")]])
            )
            return
        
        text = f"💰 充值申请列表\n\n共 {len(payments)} 条待处理：\n\n"
        
        keyboard = []
        for i, p in enumerate(payments[:5]):
            username = f"UID: {p['uid']}"
            time_str = datetime.fromisoformat(p['created_at']).strftime("%m-%d %H:%M")
            text += f"#{i+1} {username} {time_str}\n"
            keyboard.append([InlineKeyboardButton(
                f"处理 #{i+1} (UID:{p['uid']})", 
                callback_data=f"admin_payment_{p['payment_id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ 返回", callback_data="admin_back")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("admin_payment_"):
        payment_id = int(data.split("_")[-1])
        payment = await get_payment(payment_id)
        
        if not payment:
            await query.answer("申请不存在", show_alert=True)
            return
        
        created_at = datetime.fromisoformat(payment['created_at']).strftime("%Y-%m-%d %H:%M:%S")
        
        text = (
            f"💰 充值申请详情\n\n"
            f"申请编号：#{payment_id}\n"
            f"用户 UID：{payment['uid']}\n"
            f"交易哈希：{payment['tx_hash']}\n"
            f"申请时间：{created_at}\n"
            f"状态：{payment['status']}"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ 确认开通", callback_data=f"admin_approve_{payment_id}")],
            [InlineKeyboardButton("❌ 拒绝申请", callback_data=f"admin_reject_{payment_id}")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="admin_payments")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("admin_approve_"):
        payment_id = int(data.split("_")[-1])
        success = await approve_payment(payment_id, uid)
        
        if success:
            await query.edit_message_text(
                f"✅ 已批准申请 #{payment_id}，VIP 已开通",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 返回", callback_data="admin_payments")]])
            )
        else:
            await query.answer("操作失败", show_alert=True)
    
    elif data.startswith("admin_reject_"):
        payment_id = int(data.split("_")[-1])
        success = await reject_payment(payment_id, uid)
        
        if success:
            await query.edit_message_text(
                f"❌ 已拒绝申请 #{payment_id}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 返回", callback_data="admin_payments")]])
            )
        else:
            await query.answer("操作失败", show_alert=True)
    
    elif data == "admin_vip_list":
        vip_users = await get_vip_users()
        
        if not vip_users:
            await query.edit_message_text(
                "👥 VIP 用户列表\n\n暂无 VIP 用户",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 返回", callback_data="admin_back")]])
            )
            return
        
        text = f"👥 VIP 用户列表\n\n共 {len(vip_users)} 位 VIP：\n\n"
        
        for u in vip_users[:20]:
            expire = datetime.fromisoformat(u['vip_expire_at']).strftime("%Y-%m-%d")
            text += f"UID: {u['uid']} 到期: {expire}\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ 返回", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "admin_broadcast":
        context.user_data['broadcast_mode'] = True
        
        await query.edit_message_text(
            "📢 群发消息\n\n"
            "请发送要群发的消息内容：",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 取消", callback_data="admin_back")]])
        )
    
    elif data == "admin_broadcast_confirm":
        message = context.user_data.get('broadcast_message', '')
        target = context.user_data.get('broadcast_target', 'all')
        
        if target == 'all':
            users = await get_all_users()
        else:
            vip_list = await get_vip_users()
            users = [u['uid'] for u in vip_list]
        
        await query.edit_message_text(f"📤 正在发送给 {len(users)} 位用户...")
        
        success_count = 0
        for user_uid in users:
            try:
                await context.bot.send_message(chat_id=user_uid, text=message)
                success_count += 1
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"发送失败 UID:{user_uid}: {e}")
        
        await query.edit_message_text(
            f"✅ 群发完成\n\n成功发送：{success_count}/{len(users)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 返回", callback_data="admin_back")]])
        )
    
    elif data == "admin_stats":
        total_users = await get_all_users_count()
        vip_users = await get_vip_users_count()
        pending = len(await get_pending_payments())
        
        text = (
            f"📊 统计信息\n\n"
            f"• 总用户：{total_users}\n"
            f"• VIP 用户：{vip_users}\n"
            f"• 待处理充值：{pending}"
        )
        
        keyboard = [[InlineKeyboardButton("⬅️ 返回", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "admin_back":
        total_users = await get_all_users_count()
        vip_users = await get_vip_users_count()
        pending_payments = len(await get_pending_payments())
        
        text = (
            f"🔧 管理员控制面板\n\n"
            f"📊 统计：\n"
            f"• 总用户：{total_users}\n"
            f"• VIP 用户：{vip_users}\n"
            f"• 待处理充值：{pending_payments}\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("💰 充值申请列表", callback_data="admin_payments")],
            [InlineKeyboardButton("👥 VIP 用户列表", callback_data="admin_vip_list")],
            [InlineKeyboardButton("📢 群发消息", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📊 统计信息", callback_data="admin_stats")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理群发消息输入
    """
    if not context.user_data.get('broadcast_mode'):
        return
    
    if not update.effective_user or update.effective_user.id != ADMIN_UID:
        return
    
    if not update.message or not update.message.text:
        return
    
    message = update.message.text
    context.user_data['broadcast_message'] = message
    context.user_data['broadcast_mode'] = False
    
    keyboard = [
        [InlineKeyboardButton("👥 发送给所有用户", callback_data="admin_broadcast_confirm")],
        [InlineKeyboardButton("💎 仅VIP用户", callback_data="admin_broadcast_vip")],
        [InlineKeyboardButton("❌ 取消", callback_data="admin_back")]
    ]
    
    await update.message.reply_text(
        f"📢 确认发送以下消息：\n\n{message[:200]}{'...' if len(message) > 200 else ''}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def setvip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /setvip 命令：手动开通 VIP
    用法：/setvip UID 天数
    """
    if not update.effective_user or update.effective_user.id != ADMIN_UID:
        await safe_reply(update, "❌ 您没有权限执行此命令")
        return
    
    if not context.args or len(context.args) < 2:
        await safe_reply(update, "❌ 用法：/setvip UID 天数\n示例：/setvip 123456 365")
        return
    
    try:
        target_uid = int(context.args[0])
        days = int(context.args[1])
        
        if days <= 0 or days > 3650:
            await safe_reply(update, "❌ 天数必须在 1-3650 之间")
            return
    except ValueError:
        await safe_reply(update, "❌ 参数格式错误")
        return
    
    from db_manager import set_user_vip
    success = await set_user_vip(target_uid, days)
    
    if success:
        await safe_reply(update, f"✅ 已为用户 {target_uid} 开通 VIP {days} 天")
    else:
        await safe_reply(update, "❌ 开通失败")


def main() -> None:
    """
    启动 Bot
    """
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    
    if not TOKEN:
        print("❌ 错误: 未设置 TELEGRAM_BOT_TOKEN 环境变量")
        print("   请设置: export TELEGRAM_BOT_TOKEN='your_token_here'")
        print("   或创建 .env 文件: TELEGRAM_BOT_TOKEN=your_token_here")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            EXCHANGE: [
                CallbackQueryHandler(exchange_callback, pattern="^(Binance|OKX)$")
            ],
            SYMBOL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, symbol_received)
            ],
            TIMEFRAME: [
                CallbackQueryHandler(timeframe_callback, pattern="^(15m|1h|4h)$")
            ],
            INDICATOR: [
                CallbackQueryHandler(indicator_callback, pattern="^(BB|VEGAS)$")
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm_callback, pattern="^(confirm|cancel)$")
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
        conversation_timeout=CONVERSATION_TIMEOUT,
        name="subscription_conversation",
        persistent=False,
    )
    
    application.add_handler(conv_handler)
    
    application.add_handler(CallbackQueryHandler(button_callback, pattern="^(deposit_submit|vip_status|open_vip|back_vip|back_main|lang_)"))
    application.add_handler(CallbackQueryHandler(admin_button_callback, pattern="^admin_"))
    
    application.add_handler(CommandHandler("list", list_subs))
    application.add_handler(CommandHandler("delete", delete_sub))
    application.add_handler(CommandHandler("vip", vip))
    application.add_handler(CommandHandler("deposit", deposit_command))
    application.add_handler(CommandHandler("mystatus", mystatus))
    application.add_handler(CommandHandler("myid", myid))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("setvip", setvip))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message_handler))
    
    async def help_command(update, context):
        lang = await get_lang(update)
        await safe_reply(update, get_message("help", lang))
    
    application.add_handler(CommandHandler("help", help_command))
    
    application.add_error_handler(error_handler)
    
    print("🤖 CryptoSentinel Bot 已启动...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
