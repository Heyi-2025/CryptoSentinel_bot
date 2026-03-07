# -*- coding: utf-8 -*-
"""
English Language Pack
"""

MESSAGES = {
    # Common
    "welcome": "📈 CryptoSentinel Monitor\n\nPlease select exchange:",
    "help": "📖 Commands:\n\n📊 Monitoring:\n/start - Add monitor\n/list - View monitors\n/delete [id] - Delete monitor\n\n💎 VIP:\n/vip - VIP info & deposit\n/mystatus - My VIP status\n/myid - View my UID\n/language - Change language\n\nOther:\n/cancel - Cancel operation",
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
    "max_subs_reached": "❌ You have reached the subscription limit ({max}).\n\n💎 Upgrade to VIP for more slots!\nSend /vip for details",
    
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
    
    # VIP
    "vip_title": "💎 VIP Membership",
    "vip_status_vip": "✅ VIP Member\nExpires: {expire_date}",
    "vip_status_normal": "❌ Regular User",
    "vip_benefits": "📋 VIP Benefits:\n• Monitor slots: 5 (Regular: 1)\n• Duration: {duration} days",
    "vip_price": "💰 Price: {price} USDT",
    "vip_deposit_address": "📍 Deposit Address (TRC20):\n<code>{address}</code>",
    "vip_deposit_hint": "⚠️ After transfer, click the button below to submit",
    
    # VIP Status
    "mystatus_title": "📊 VIP Status",
    "mystatus_vip": "✅ VIP Member\nExpires: {expire_date} ({days_left} days left)",
    "mystatus_normal": "❌ Regular User\nQuota: 1 indicator",
    "mystatus_quota": "Indicator quota: {current}/{max}",
    "mystatus_register_date": "Registered: {date}",
    
    # Deposit
    "deposit_hint": "📝 Submit Deposit Request\n\nPlease send transaction hash:\nFormat: /deposit tx_hash\n\nExample:\n/deposit abc123def456789...",
    "deposit_missing_hash": "❌ Please provide transaction hash\n\nUsage: /deposit tx_hash\nExample: /deposit abc123def456...",
    "deposit_hash_too_short": "❌ Invalid transaction hash format",
    "deposit_success": "✅ Deposit request submitted!\n\nTransaction: {tx_hash}...\nRequest ID: #{payment_id}\n\nPlease wait for admin approval. VIP will be activated automatically.",
    
    # Open VIP
    "open_vip_title": "💎 Get VIP",
    "open_vip_price": "Price: {price} USDT / {duration} days",
    
    # Admin
    "admin_no_permission": "❌ You don't have permission to access admin panel",
    "admin_panel": "🔧 Admin Control Panel\n\n📊 Stats:\n• Total users: {total}\n• VIP users: {vip}\n• Pending deposits: {pending}\n",
    "admin_setvip_usage": "❌ Usage: /setvip UID days\nExample: /setvip 123456 365",
    "admin_setvip_success": "✅ VIP activated for user {uid} ({days} days)",
    "admin_setvip_failed": "❌ Activation failed",
    "admin_setvip_param_error": "❌ Invalid parameters",
    
    # Admin buttons
    "admin_btn_payments": "💰 Deposit Requests",
    "admin_btn_vip_list": "👥 VIP Users",
    "admin_btn_broadcast": "📢 Broadcast",
    "admin_btn_stats": "📊 Statistics",
    "admin_btn_back": "⬅️ Back",
    
    # Payment requests
    "admin_payments_title": "💰 Deposit Requests\n\n{count} pending:\n\n",
    "admin_payments_empty": "💰 Deposit Requests\n\nNo pending requests",
    "admin_payment_detail": "💰 Deposit Request Details\n\nRequest ID: #{payment_id}\nUser UID: {uid}\nTransaction: {tx_hash}\nTime: {time}\nStatus: {status}",
    "admin_payment_approved": "✅ Request #{payment_id} approved, VIP activated",
    "admin_payment_rejected": "❌ Request #{payment_id} rejected",
    
    # VIP list
    "admin_vip_list_title": "👥 VIP Users\n\n{count} VIP members:\n\n",
    "admin_vip_list_empty": "👥 VIP Users\n\nNo VIP users yet",
    
    # Broadcast
    "admin_broadcast_input": "📢 Broadcast Message\n\nPlease enter the message to send:",
    "admin_broadcast_confirm": "📢 Confirm sending:\n\n{message}",
    "admin_broadcast_sending": "📤 Sending to {count} users...",
    "admin_broadcast_done": "✅ Broadcast complete\n\nSent: {success}/{total}",
    
    # Stats
    "admin_stats": "📊 Statistics\n\n• Total users: {total}\n• VIP users: {vip}\n• Pending deposits: {pending}",
    
    # Language
    "language_select": "🌐 选择语言 / Select language:",
    "language_changed": "✅ Language changed",
    "btn_lang_zh": "🇨🇳 中文",
    "btn_lang_en": "🇺🇸 English",
    
    # Buttons
    "btn_submit_deposit": "📝 Submit Deposit",
    "btn_vip_status": "📊 My VIP Status",
    "btn_open_vip": "💎 Get VIP",
    "btn_confirm": "✅ Confirm",
    "btn_cancel": "❌ Cancel",
    "btn_approve": "✅ Approve",
    "btn_reject": "❌ Reject",
    "btn_broadcast_all": "👥 All Users",
    "btn_broadcast_vip": "💎 VIP Only",
    
    # VIP Expiry Reminder
    "vip_reminder": "⏰ VIP Expiry Reminder\n\nYour VIP will expire in {days} days\n\n💎 Renewal: {price} USDT / {duration} days\n\n📍 Deposit Address (TRC20):\n<code>{address}</code>\n\nAfter transfer, send /deposit tx_hash to submit",
    "vip_expired": "❌ VIP Expired\n\nYour VIP has expired. You are now a regular user.\nMonitor quota: 1 indicator\n\n💎 Reactivate: {price} USDT / {duration} days\n\n📍 Deposit Address (TRC20):\n<code>{address}</code>\n\nAfter transfer, send /deposit tx_hash to submit",
    
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