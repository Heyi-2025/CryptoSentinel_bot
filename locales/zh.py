# -*- coding: utf-8 -*-
"""
中文语言包
"""

MESSAGES = {
    # 主菜单
    "main_menu": "📈 CryptoSentinel 监控系统\n\n请选择功能：",
    "btn_add_monitor": "➕ 添加监控",
    "btn_my_monitors": "📋 我的监控",
    "btn_my_uid": "🆔 我的UID",
    "btn_contact": "👨‍💻 联系开发者",
    "btn_language": "🌐 语言",
    "btn_help": "❓ 帮助",
    "btn_donate": "☕ 打赏开发者",
    "contact_developer": "👨‍💻 联系开发者\n\nTelegram: @wxyybw\n\n如有问题或建议，欢迎联系！",
    
    # 订阅成功（带价格）
    "confirm_saved_with_price": "✅ 监控添加成功！\n\n💰 当前价格：{price} USDT\n\n📋 订阅详情：\n• 交易所：{exchange}\n• 交易对：{symbol}\n• 周期：{timeframe}\n• 指标：{indicator}\n\n💡 使用 /list 查看所有监控",
    "confirm_saved_no_price": "✅ 监控添加成功！\n\n📋 订阅详情：\n• 交易所：{exchange}\n• 交易对：{symbol}\n• 周期：{timeframe}\n• 指标：{indicator}\n\n💡 使用 /list 查看所有监控",
    
    # 通用
    "welcome": "📈 CryptoSentinel 监控系统\n\n请选择交易所：",
    "help": "📖 命令列表：\n\n📊 监控功能：\n/start - 添加监控\n/list - 查看监控列表\n/delete [编号] - 删除监控\n\n🆔 用户信息：\n/myid - 查看我的UID\n/language - 切换语言\n\n☕ 支持开发：\n/donate - 打赏开发者\n\n其他：\n/cancel - 取消操作",
    "cancel": "❌ 操作已取消",
    
    # 交易所选择
    "select_exchange": "请选择交易所：",
    "exchange_selected": "✅ 交易所: {exchange}\n\n请输入交易对（如 BTC/USDT, ETH/USDT）：",
    
    # 交易对
    "symbol_format_error": "❌ 格式错误，请输入如 BTC/USDT",
    "symbol_quote_warning": "⚠️ 警告: {quote} 不是常用报价币种\n支持的报价币种: {valid_quotes}\n继续添加请忽略此警告",
    "symbol_selected": "✅ 交易对: {symbol}\n\n请选择时间周期：",
    
    # 时间周期
    "timeframe_selected": "✅ 交易对: {symbol}\n✅ 时间周期: {timeframe}\n\n请选择技术指标：",
    
    # 指标
    "indicator_bb": "BB 布林带",
    "indicator_vegas": "VEGAS 通道",
    "indicator_selected": "📋 确认您的监控配置：\n\n• 交易所: {exchange}\n• 交易对: {symbol}\n• 时间周期: {timeframe}\n• 技术指标: {indicator}\n\n请确认是否保存？",
    
    # 确认
    "confirm_saved": "✅ 配置已保存！\n\nSub ID: {sub_id}\n交易所: {exchange}\n交易对: {symbol}\n周期: {timeframe}\n指标: {indicator}",
    "confirm_cancelled": "❌ 已取消操作",
    "data_incomplete": "❌ 数据不完整，请重新开始 /start",
    "save_failed": "❌ 保存失败，请重试",
    
    # 订阅限制
    "max_subs_reached": "❌ 您已达到订阅上限 ({max} 个)。",
    
    # 订阅列表
    "no_subs": "📭 您当前没有任何监控任务\n\n发送 /start 添加新监控",
    "subs_list": "📋 您的监控任务列表：\n\n",
    "subs_list_footer": "\n💡 使用 /delete [编号] 删除任务",
    
    # 删除订阅
    "delete_success": "✅ 已删除监控任务 #{sub_id}",
    "delete_failed": "❌ 删除失败，请重试",
    "delete_not_found": "❌ 无法删除：该任务不存在或不属于您",
    "delete_invalid_id": "❌ 请指定要删除的任务编号\n\n用法：/delete 123",
    "delete_not_number": "❌ 编号必须是数字\n\n用法：/delete 123",
    
    # 用户ID
    "myid": "🆔 您的用户信息：\n\n• UID: {uid}\n• 用户名: @{username}",
    
    # 打赏
    "donate_title": "☕ 打赏开发者",
    "donate_content": "感谢您使用 CryptoSentinel！\n\n如果这个项目对您有帮助，欢迎打赏支持开发者 ❤️\n\n📍 打赏地址 (TRC20)：\n<code>{address}</code>\n\n💰 USDT (TRC20)\n\n您的支持是我持续更新的动力！",
    "donate_copy": "📋 地址已复制到剪贴板",
    
    # 管理员
    "admin_no_permission": "❌ 您没有权限访问管理员面板",
    "admin_panel": "🔧 管理员控制面板\n\n📊 统计：\n• 总用户：{total}\n",
    "admin_btn_broadcast": "📢 群发消息",
    "admin_btn_stats": "📊 统计信息",
    "admin_btn_back": "⬅️ 返回",
    
    # 群发
    "admin_broadcast_input": "📢 群发消息\n\n请发送要群发的消息内容：",
    "admin_broadcast_confirm": "📢 确认发送以下消息：\n\n{message}",
    "admin_broadcast_sending": "📤 正在发送给 {count} 位用户...",
    "admin_broadcast_done": "✅ 群发完成\n\n成功发送：{success}/{total}",
    
    # 统计
    "admin_stats": "📊 统计信息\n\n• 总用户：{total}",
    
    # 语言
    "language_select": "🌐 选择语言 / Select language:",
    "language_changed": "✅ 语言已切换",
    "btn_lang_zh": "🇨🇳 中文",
    "btn_lang_en": "🇺🇸 English",
    
    # 按钮
    "btn_confirm": "✅ 确认",
    "btn_cancel": "❌ 取消",
    "btn_broadcast_all": "👥 发送给所有用户",
    
    # 错误
    "error_user_not_found": "❌ 用户信息不存在，请先发送 /start",
    "error_operation_failed": "❌ 操作失败，请重试",
    "error_timeout": "❌ 操作超时或出错，请重新输入 /start",
    
    # VEGAS 触碰信号
    "vegas_cross_up_144": "⬆️ VEGAS 上穿信号\n{symbol} K线穿过 EMA144 ({ema:.2f})\n方向：向上",
    "vegas_cross_down_144": "⬇️ VEGAS 下穿信号\n{symbol} K线跌破 EMA144 ({ema:.2f})\n方向：向下",
    "vegas_cross_up_169": "⬆️ VEGAS 上穿信号\n{symbol} K线穿过 EMA169 ({ema:.2f})\n方向：向上",
    "vegas_cross_down_169": "⬇️ VEGAS 下穿信号\n{symbol} K线跌破 EMA169 ({ema:.2f})\n方向：向下",
    
    # 币种验证
    "symbol_not_supported": "❌ 该交易对不被支持\n\n支持的交易对：\n{symbols}\n\n请从上方列表中选择",
    "symbol_loading": "⏳ 正在获取支持的交易对...",
}