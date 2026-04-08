"""
Telegram Bot 前端交互模块
使用 python-telegram-bot v20+ 的 Application 和 ConversationHandler
"""
import asyncio
import logging
import os
import time
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
    get_user_info, get_all_users, get_all_users_count,
    ADMIN_UID, get_user_language, set_user_language, MAX_SUBSCRIPTIONS
)

from i18n import get_message, detect_language, get_button_text
import ccxt.async_support as ccxt


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DONATE_ADDRESS = os.environ.get("DONATE_ADDRESS", "TQ66Jy7fgubE9H3dj981gfqnEfodSBVPfx")

SUPPORTED_SYMBOLS_CACHE = set()
SUPPORTED_SYMBOLS_CACHE_TIME = 0
SUPPORTED_SYMBOLS_CACHE_TTL = 3600

(
    EXCHANGE,
    SYMBOL,
    TIMEFRAME,
    INDICATOR,
    CONFIRM,
) = range(5)

CONVERSATION_TIMEOUT = 120


async def get_lang(update: Update) -> str:
    """获取用户的语言设置"""
    if not update.effective_user:
        return "zh"
    uid = update.effective_user.id
    lang = await get_user_language(uid)
    if lang:
        return lang
    lang_code = update.effective_user.language_code
    return detect_language(lang_code)


async def safe_reply(update: Update, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> None:
    """安全发送消息"""
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def safe_edit(update: Update, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> None:
    """安全编辑消息"""
    query = update.callback_query
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """全局错误处理"""
    logger.error(f"处理更新时发生错误: {context.error}")
    try:
        lang = await get_lang(update) if update else "zh"
        await safe_reply(update, get_message("error_timeout", lang))
    except Exception:
        pass


async def fetch_okx_symbols() -> set:
    """从 OKX API 获取支持的交易对列表"""
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
    """获取支持的交易对列表（带缓存）"""
    global SUPPORTED_SYMBOLS_CACHE, SUPPORTED_SYMBOLS_CACHE_TIME
    current_time = time.time()
    if SUPPORTED_SYMBOLS_CACHE and (current_time - SUPPORTED_SYMBOLS_CACHE_TIME) < SUPPORTED_SYMBOLS_CACHE_TTL:
        return SUPPORTED_SYMBOLS_CACHE
    symbols = await fetch_okx_symbols()
    if symbols:
        SUPPORTED_SYMBOLS_CACHE = symbols
        SUPPORTED_SYMBOLS_CACHE_TIME = current_time
    return SUPPORTED_SYMBOLS_CACHE


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/start 命令入口"""
    try:
        if not update.effective_user:
            return ConversationHandler.END
        uid = update.effective_user.id
        lang = await get_lang(update)
        await add_user(uid)
        sub_count = await get_user_sub_count(uid)
        if sub_count >= MAX_SUBSCRIPTIONS:
            await safe_reply(update, get_message("max_subs_reached", lang, max=MAX_SUBSCRIPTIONS))
            return ConversationHandler.END
        keyboard = [[InlineKeyboardButton("Binance", callback_data="Binance"), InlineKeyboardButton("OKX", callback_data="OKX")]]
        await safe_reply(update, get_message("welcome", lang), reply_markup=InlineKeyboardMarkup(keyboard))
        return EXCHANGE
    except Exception as e:
        logger.error(f"start 命令异常: {e}")
        return ConversationHandler.END


async def exchange_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理交易所选择"""
    try:
        query = update.callback_query
        if not query:
            return ConversationHandler.END
        await query.answer()
        exchange = query.data
        context.user_data["exchange"] = exchange
        lang = await get_lang(update)
        await safe_edit(update, get_message("exchange_selected", lang, exchange=exchange))
        return SYMBOL
    except Exception as e:
        logger.error(f"exchange_callback 异常: {e}")
        return ConversationHandler.END


async def symbol_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理交易对输入"""
    try:
        if not update.message:
            return ConversationHandler.END
        lang = await get_lang(update)
        symbol = update.message.text.strip().upper()
        if not symbol or "/" not in symbol or len(symbol) > 20:
            await update.message.reply_text(get_message("symbol_format_error", lang))
            return SYMBOL
        parts = symbol.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            await update.message.reply_text(get_message("symbol_format_error", lang))
            return SYMBOL
        supported_symbols = await get_supported_symbols()
        if supported_symbols and symbol not in supported_symbols:
            popular = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT", "LINK/USDT"]
            available = [s for s in popular if s in supported_symbols][:10]
            await update.message.reply_text(get_message("symbol_not_supported", lang, symbols="\n".join(available)))
            return SYMBOL
        context.user_data["symbol"] = symbol
        keyboard = [[InlineKeyboardButton("15m", callback_data="15m"), InlineKeyboardButton("1h", callback_data="1h"), InlineKeyboardButton("4h", callback_data="4h")]]
        await update.message.reply_text(get_message("symbol_selected", lang, symbol=symbol), reply_markup=InlineKeyboardMarkup(keyboard))
        return TIMEFRAME
    except Exception as e:
        logger.error(f"symbol_received 异常: {e}")
        return ConversationHandler.END


async def timeframe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理时间周期选择"""
    try:
        query = update.callback_query
        if not query:
            return ConversationHandler.END
        await query.answer()
        timeframe = query.data
        context.user_data["timeframe"] = timeframe
        keyboard = [[InlineKeyboardButton(get_message("indicator_bb", await get_lang(update)), callback_data="BB"), InlineKeyboardButton(get_message("indicator_vegas", await get_lang(update)), callback_data="VEGAS"), InlineKeyboardButton(get_message("indicator_ma_density", await get_lang(update)), callback_data="MA_DENSITY")]]
        symbol = context.user_data.get("symbol", "")
        await safe_edit(update, get_message("timeframe_selected", await get_lang(update), symbol=symbol, timeframe=timeframe), reply_markup=InlineKeyboardMarkup(keyboard))
        return INDICATOR
    except Exception as e:
        logger.error(f"timeframe_callback 异常: {e}")
        return ConversationHandler.END


async def indicator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理指标选择"""
    try:
        query = update.callback_query
        if not query:
            return ConversationHandler.END
        await query.answer()
        indicator = query.data
        context.user_data["indicator"] = indicator
        lang = await get_lang(update)
        text = get_message("indicator_selected", lang, exchange=context.user_data.get("exchange", ""), symbol=context.user_data.get("symbol", ""), timeframe=context.user_data.get("timeframe", ""), indicator=indicator)
        keyboard = [[InlineKeyboardButton(get_button_text("btn_confirm", lang), callback_data="confirm"), InlineKeyboardButton(get_button_text("btn_cancel", lang), callback_data="cancel")]]
        await safe_edit(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return CONFIRM
    except Exception as e:
        logger.error(f"indicator_callback 异常: {e}")
        return ConversationHandler.END


async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理确认"""
    try:
        query = update.callback_query
        if not query:
            return ConversationHandler.END
        await query.answer()
        lang = await get_lang(update)
        if query.data == "cancel":
            await safe_edit(update, get_message("confirm_cancelled", lang))
            return ConversationHandler.END
        uid = update.effective_user.id
        exchange = context.user_data.get("exchange")
        symbol = context.user_data.get("symbol")
        timeframe = context.user_data.get("timeframe")
        indicator = context.user_data.get("indicator")
        if not all([exchange, symbol, timeframe, indicator]):
            await safe_edit(update, get_message("data_incomplete", lang))
            return ConversationHandler.END
        sub_id = await add_subscription(uid, exchange, symbol, timeframe, indicator)
        await safe_edit(update, get_message("confirm_saved", lang, sub_id=sub_id, exchange=exchange, symbol=symbol, timeframe=timeframe, indicator=indicator))
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"confirm_callback 异常: {e}")
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """取消对话"""
    lang = await get_lang(update)
    await safe_reply(update, get_message("cancel", lang))
    return ConversationHandler.END


async def list_subs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/list 命令"""
    try:
        if not update.effective_user:
            return
        lang = await get_lang(update)
        uid = update.effective_user.id
        subs = await get_user_subs(uid)
        if not subs:
            await safe_reply(update, get_message("no_subs", lang))
            return
        text = get_message("subs_list", lang)
        for sub in subs:
            status = "✅" if sub["is_active"] else "❌"
            text += f"{status} #{sub['sub_id']} {sub['exchange']} {sub['symbol']}\n   周期: {sub['timeframe']} | 指标: {sub['indicator']}\n\n"
        text += get_message("subs_list_footer", lang)
        await safe_reply(update, text)
    except Exception as e:
        logger.error(f"list_subs 异常: {e}")


async def delete_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/delete 命令"""
    try:
        if not update.effective_user:
            return
        lang = await get_lang(update)
        if not context.args:
            await safe_reply(update, get_message("delete_invalid_id", lang))
            return
        try:
            sub_id = int(context.args[0])
        except ValueError:
            await safe_reply(update, get_message("delete_not_number", lang))
            return
        uid = update.effective_user.id
        user_subs = await get_user_subs(uid)
        valid_ids = [s["sub_id"] for s in user_subs]
        if sub_id not in valid_ids:
            await safe_reply(update, get_message("delete_not_found", lang))
            return
        success = await delete_subscription(sub_id, uid)
        if success:
            await safe_reply(update, get_message("delete_success", lang, sub_id=sub_id))
        else:
            await safe_reply(update, get_message("delete_failed", lang))
    except Exception as e:
        logger.error(f"delete_sub 异常: {e}")


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/myid 命令"""
    if not update.effective_user:
        return
    lang = await get_lang(update)
    uid = update.effective_user.id
    username = update.effective_user.username or ("未设置" if lang == "zh" else "Not set")
    await safe_reply(update, get_message("myid", lang, uid=uid, username=username))


async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/donate 命令 - 显示打赏地址"""
    if not update.effective_user:
        return
    lang = await get_lang(update)
    text = get_message("donate_content", lang, address=DONATE_ADDRESS)
    await safe_reply(update, text)


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/language 命令 - 切换语言"""
    lang = await get_lang(update)
    keyboard = [[InlineKeyboardButton(get_button_text("btn_lang_zh", lang), callback_data="lang_zh")], [InlineKeyboardButton(get_button_text("btn_lang_en", lang), callback_data="lang_en")]]
    await safe_reply(update, get_message("language_select", lang), reply_markup=InlineKeyboardMarkup(keyboard))


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理按钮回调"""
    query = update.callback_query
    if not query:
        return
    await query.answer()
    uid = update.effective_user.id
    data = query.data
    if data.startswith("lang_"):
        new_lang = data.split("_")[-1]
        await set_user_language(uid, new_lang)
        await query.edit_message_text(get_message("language_changed", new_lang))


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin 命令 - 管理员面板"""
    if not update.effective_user:
        return
    uid = update.effective_user.id
    if uid != ADMIN_UID:
        lang = await get_lang(update)
        await safe_reply(update, get_message("admin_no_permission", lang))
        return
    lang = await get_lang(update)
    total_users = await get_all_users_count()
    text = get_message("admin_panel", lang, total=total_users)
    keyboard = [[InlineKeyboardButton(get_button_text("admin_btn_broadcast", lang), callback_data="admin_broadcast")], [InlineKeyboardButton(get_button_text("admin_btn_stats", lang), callback_data="admin_stats")], [InlineKeyboardButton(get_button_text("admin_btn_back", lang), callback_data="admin_back")]]
    await safe_reply(update, text, reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理管理员按钮"""
    query = update.callback_query
    if not query:
        return
    uid = update.effective_user.id
    if uid != ADMIN_UID:
        await query.answer("❌ 无权限", show_alert=True)
        return
    await query.answer()
    data = query.data
    lang = await get_lang(update)
    
    if data == "admin_broadcast":
        context.user_data['broadcast_mode'] = True
        keyboard = [[InlineKeyboardButton(get_button_text("admin_btn_back", lang), callback_data="admin_back")]]
        await query.edit_message_text(get_message("admin_broadcast_input", lang), reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "admin_stats":
        total_users = await get_all_users_count()
        text = get_message("admin_stats", lang, total=total_users)
        keyboard = [[InlineKeyboardButton(get_button_text("admin_btn_back", lang), callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "admin_back":
        total_users = await get_all_users_count()
        text = get_message("admin_panel", lang, total=total_users)
        keyboard = [[InlineKeyboardButton(get_button_text("admin_btn_broadcast", lang), callback_data="admin_broadcast")], [InlineKeyboardButton(get_button_text("admin_btn_stats", lang), callback_data="admin_stats")], [InlineKeyboardButton(get_button_text("admin_btn_back", lang), callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理群发消息输入"""
    if not context.user_data.get('broadcast_mode'):
        return
    if not update.effective_user or update.effective_user.id != ADMIN_UID:
        return
    if not update.message or not update.message.text:
        return
    lang = await get_lang(update)
    message = update.message.text
    context.user_data['broadcast_message'] = message
    context.user_data['broadcast_mode'] = False
    keyboard = [[InlineKeyboardButton(get_button_text("btn_broadcast_all", lang), callback_data="admin_broadcast_confirm")], [InlineKeyboardButton(get_button_text("admin_btn_back", lang), callback_data="admin_back")]]
    await update.message.reply_text(get_message("admin_broadcast_confirm", lang, message=message[:200]), reply_markup=InlineKeyboardMarkup(keyboard))


def main() -> None:
    """启动 Bot"""
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not TOKEN:
        print("❌ 错误: 未设置 TELEGRAM_BOT_TOKEN")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            EXCHANGE: [CallbackQueryHandler(exchange_callback, pattern="^(Binance|OKX)$")],
            SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, symbol_received)],
            TIMEFRAME: [CallbackQueryHandler(timeframe_callback, pattern="^(15m|1h|4h)$")],
            INDICATOR: [CallbackQueryHandler(indicator_callback, pattern="^(BB|VEGAS|MA_DENSITY)$")],
            CONFIRM: [CallbackQueryHandler(confirm_callback, pattern="^(confirm|cancel)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        conversation_timeout=CONVERSATION_TIMEOUT,
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(admin_button_callback, pattern="^admin_"))
    application.add_handler(CommandHandler("list", list_subs))
    application.add_handler(CommandHandler("delete", delete_sub))
    application.add_handler(CommandHandler("myid", myid))
    application.add_handler(CommandHandler("donate", donate))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message_handler))
    
    async def help_command(update, context):
        lang = await get_lang(update)
        help_text = get_message("help", lang) + f"\n\n☕ 支持作者: /donate"
        await safe_reply(update, help_text)
    
    application.add_handler(CommandHandler("help", help_command))
    application.add_error_handler(error_handler)
    
    print("🤖 CryptoSentinel Bot 已启动...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()