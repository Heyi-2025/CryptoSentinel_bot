# -*- coding: utf-8 -*-
"""
English Language Pack
"""

MESSAGES = {
    # Main Menu
    "main_menu": "📈 CryptoSentinel Monitor\n\nPlease select a function:",
    "btn_add_monitor": "➕ Add Monitor",
    "btn_my_monitors": "📋 My Monitors",
    "btn_my_uid": "🆔 My UID",
    "btn_contact": "👨‍💻 Contact Dev",
    "btn_language": "🌐 Language",
    "btn_help": "❓ Help",
    "btn_donate": "☕ Donate",
    "contact_developer": "👨‍💻 Contact Developer\n\nTelegram: @wxyybw\n\nFeel free to reach out for questions or suggestions!",
    
    # Subscription success (with price)
    "confirm_saved_with_price": "✅ Monitor added successfully!\n\n💰 Current Price: {price} USDT\n\n📋 Details:\n• Exchange: {exchange}\n• Symbol: {symbol}\n• Timeframe: {timeframe}\n• Indicator: {indicator}\n\n💡 Use /list to view all monitors",
    "confirm_saved_no_price": "✅ Monitor added successfully!\n\n📋 Details:\n• Exchange: {exchange}\n• Symbol: {symbol}\n• Timeframe: {timeframe}\n• Indicator: {indicator}\n\n💡 Use /list to view all monitors",
    
    # Common
    "welcome": "📈 CryptoSentinel Monitor\n\nPlease select exchange:",
    "help": "📖 Commands:\n\n📊 Monitoring:\n/start - Add monitor\n/list - View monitors\n/delete [id] - Delete monitor\n\n🆔 User Info:\n/myid - View my UID\n/language - Change language\n\n☕ Support:\n/donate - Support the developer\n\nOther:\n/cancel - Cancel operation",
    "cancel": "❌ Operation cancelled",
    
    # Exchange selection
    "select_exchange": "Please select exchange:",
    "exchange_selected": "✅ Exchange: {exchange}\n\nPlease enter trading pair (e.g. BTC/USDT, ETH/USDT):",
    
    # Symbol
    "symbol_format_error": "❌ Format error, please enter like BTC/USDT",
    "symbol_quote_warning": "⚠️ Warning: {quote} is not a common quote currency\nSupported: {valid_quotes}\nYou can still continue",
    "symbol_selected": "✅ Symbol: {symbol}\n\nPlease select timeframe:",
    
    # Timeframe
    "timeframe_selected": "✅ Symbol: {symbol}\n✅ Timeframe: {timeframe}\n\nPlease select indicator:",
    
    # Indicator
    "indicator_bb": "BB Bollinger Bands",
    "indicator_vegas": "VEGAS Tunnel",
    "indicator_selected": "📋 Confirm your monitor settings:\n\n• Exchange: {exchange}\n• Symbol: {symbol}\n• Timeframe: {timeframe}\n• Indicator: {indicator}\n\nSave this configuration?",
    
    # Confirm
    "confirm_saved": "✅ Configuration saved!\n\nSub ID: {sub_id}\nExchange: {exchange}\nSymbol: {symbol}\nTimeframe: {timeframe}\nIndicator: {indicator}",
    "confirm_cancelled": "❌ Operation cancelled",
    "data_incomplete": "❌ Data incomplete, please restart with /start",
    "save_failed": "❌ Save failed, please try again",
    
    # Subscription limit
    "max_subs_reached": "❌ You have reached the subscription limit ({max}).",
    
    # Subscription list
    "no_subs": "📭 You have no monitors yet\n\nSend /start to add one",
    "subs_list": "📋 Your monitors:\n\n",
    "subs_list_footer": "\n💡 Use /delete [id] to remove",
    
    # Delete subscription
    "delete_success": "✅ Monitor #{sub_id} deleted",
    "delete_failed": "❌ Delete failed, please try again",
    "delete_not_found": "❌ Cannot delete: monitor not found or not yours",
    "delete_invalid_id": "❌ Please specify the monitor ID\n\nUsage: /delete 123",
    "delete_not_number": "❌ ID must be a number\n\nUsage: /delete 123",
    
    # User ID
    "myid": "🆔 Your info:\n\n• UID: {uid}\n• Username: @{username}",
    
    # Donate
    "donate_title": "☕ Support the Developer",
    "donate_content": "Thank you for using CryptoSentinel!\n\nIf this project helps you, consider buying me a coffee ❤️\n\n📍 Donate Address (TRC20):\n<code>{address}</code>\n\n💰 USDT (TRC20)\n\nYour support keeps me motivated to improve!",
    "donate_copy": "📋 Address copied to clipboard",
    
    # Admin
    "admin_no_permission": "❌ You don't have permission to access admin panel",
    "admin_panel": "🔧 Admin Control Panel\n\n📊 Stats:\n• Total users: {total}\n",
    "admin_btn_broadcast": "📢 Broadcast",
    "admin_btn_stats": "📊 Statistics",
    "admin_btn_back": "⬅️ Back",
    
    # Broadcast
    "admin_broadcast_input": "📢 Broadcast Message\n\nPlease enter the message to send:",
    "admin_broadcast_confirm": "📢 Confirm sending:\n\n{message}",
    "admin_broadcast_sending": "📤 Sending to {count} users...",
    "admin_broadcast_done": "✅ Broadcast complete\n\nSent: {success}/{total}",
    
    # Stats
    "admin_stats": "📊 Statistics\n\n• Total users: {total}",
    
    # Language
    "language_select": "🌐 选择语言 / Select language:",
    "language_changed": "✅ Language changed",
    "btn_lang_zh": "🇨🇳 中文",
    "btn_lang_en": "🇺🇸 English",
    
    # Buttons
    "btn_confirm": "✅ Confirm",
    "btn_cancel": "❌ Cancel",
    "btn_broadcast_all": "👥 All Users",
    
    # Errors
    "error_user_not_found": "❌ User not found, please send /start first",
    "error_operation_failed": "❌ Operation failed, please try again",
    "error_timeout": "❌ Timeout or error, please restart with /start",
    
    # VEGAS Cross Signals
    "vegas_cross_up_144": "⬆️ VEGAS Cross Up\n{symbol} K-line crossed EMA144 ({ema:.2f})\nDirection: Up",
    "vegas_cross_down_144": "⬇️ VEGAS Cross Down\n{symbol} K-line broke EMA144 ({ema:.2f})\nDirection: Down",
    "vegas_cross_up_169": "⬆️ VEGAS Cross Up\n{symbol} K-line crossed EMA169 ({ema:.2f})\nDirection: Up",
    "vegas_cross_down_169": "⬇️ VEGAS Cross Down\n{symbol} K-line broke EMA169 ({ema:.2f})\nDirection: Down",
    
    # Symbol Validation
    "symbol_not_supported": "❌ Trading pair not supported\n\nSupported pairs:\n{symbols}\n\nPlease select from the list above",
    "symbol_loading": "⏳ Loading supported trading pairs...",
}