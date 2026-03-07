# -*- coding: utf-8 -*-
"""
中文语言包
"""

MESSAGES = {
    # 通用
    "welcome": "📈 CryptoSentinel 监控系统\n\n请选择交易所：",
    "help": "📖 命令列表：\n\n📊 监控功能：\n/start - 添加监控\n/list - 查看监控列表\n/delete [编号] - 删除监控\n\n💎 VIP功能：\n/vip - VIP说明和充值\n/mystatus - 我的VIP状态\n/myid - 查看我的UID\n/language - 切换语言\n\n其他：\n/cancel - 取消操作",
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
    "max_subs_reached": "❌ 您已达到订阅上限 ({max} 个)。\n\n💎 升级 VIP 可获得更多配额！\n发送 /vip 了解详情",
    
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
    
    # VIP
    "vip_title": "💎 VIP 会员",
    "vip_status_vip": "✅ VIP 会员\n到期时间: {expire_date}",
    "vip_status_normal": "❌ 普通用户",
    "vip_benefits": "📋 VIP 权益：\n• 监控指标：5个（普通用户 1个）\n• 有效期：{duration} 天",
    "vip_price": "💰 价格：{price} USDT",
    "vip_deposit_address": "📍 充值地址 (TRC20)：\n<code>{address}</code>",
    "vip_deposit_hint": "⚠️ 转账后请点击下方按钮提交申请",
    
    # VIP状态
    "mystatus_title": "📊 VIP 状态",
    "mystatus_vip": "✅ VIP 会员\n到期时间: {expire_date}\n剩余: {days_left} 天",
    "mystatus_normal": "❌ 普通用户\n配额: 1 个指标",
    "mystatus_quota": "指标配额：{current}/{max}",
    "mystatus_register_date": "注册时间：{date}",
    
    # 充值
    "deposit_hint": "📝 提交充值申请\n\n请发送交易哈希：\n格式：/deposit 交易哈希\n\n示例：\n/deposit abc123def456789...",
    "deposit_missing_hash": "❌ 请提供交易哈希\n\n用法：/deposit 交易哈希\n示例：/deposit abc123def456...",
    "deposit_hash_too_short": "❌ 交易哈希格式错误，请检查后重试",
    "deposit_success": "✅ 充值申请已提交！\n\n交易哈希：{tx_hash}...\n申请编号：#{payment_id}\n\n请等待管理员审核，审核通过后将自动开通 VIP。",
    
    # 开通VIP
    "open_vip_title": "💎 开通 VIP",
    "open_vip_price": "价格：{price} USDT / {duration} 天",
    
    # 管理员
    "admin_no_permission": "❌ 您没有权限访问管理员面板",
    "admin_panel": "🔧 管理员控制面板\n\n📊 统计：\n• 总用户：{total}\n• VIP 用户：{vip}\n• 待处理充值：{pending}\n",
    "admin_setvip_usage": "❌ 用法：/setvip UID 天数\n示例：/setvip 123456 365",
    "admin_setvip_success": "✅ 已为用户 {uid} 开通 VIP {days} 天",
    "admin_setvip_failed": "❌ 开通失败",
    "admin_setvip_param_error": "❌ 参数格式错误",
    
    # 管理员按钮
    "admin_btn_payments": "💰 充值申请列表",
    "admin_btn_vip_list": "👥 VIP 用户列表",
    "admin_btn_broadcast": "📢 群发消息",
    "admin_btn_stats": "📊 统计信息",
    "admin_btn_back": "⬅️ 返回",
    
    # 充值申请
    "admin_payments_title": "💰 充值申请列表\n\n共 {count} 条待处理：\n\n",
    "admin_payments_empty": "💰 充值申请列表\n\n暂无待处理的申请",
    "admin_payment_detail": "💰 充值申请详情\n\n申请编号：#{payment_id}\n用户 UID：{uid}\n交易哈希：{tx_hash}\n申请时间：{time}\n状态：{status}",
    "admin_payment_approved": "✅ 已批准申请 #{payment_id}，VIP 已开通",
    "admin_payment_rejected": "❌ 已拒绝申请 #{payment_id}",
    
    # VIP用户列表
    "admin_vip_list_title": "👥 VIP 用户列表\n\n共 {count} 位 VIP：\n\n",
    "admin_vip_list_empty": "👥 VIP 用户列表\n\n暂无 VIP 用户",
    
    # 群发
    "admin_broadcast_input": "📢 群发消息\n\n请发送要群发的消息内容：",
    "admin_broadcast_confirm": "📢 确认发送以下消息：\n\n{message}",
    "admin_broadcast_sending": "📤 正在发送给 {count} 位用户...",
    "admin_broadcast_done": "✅ 群发完成\n\n成功发送：{success}/{total}",
    
    # 统计
    "admin_stats": "📊 统计信息\n\n• 总用户：{total}\n• VIP 用户：{vip}\n• 待处理充值：{pending}",
    
    # 语言
    "language_select": "🌐 选择语言 / Select language:",
    "language_changed": "✅ 语言已切换",
    "btn_lang_zh": "🇨🇳 中文",
    "btn_lang_en": "🇺🇸 English",
    
    # 按钮
    "btn_submit_deposit": "📝 提交充值申请",
    "btn_vip_status": "📊 我的VIP状态",
    "btn_open_vip": "💎 开通VIP",
    "btn_confirm": "✅ 确认",
    "btn_cancel": "❌ 取消",
    "btn_approve": "✅ 确认开通",
    "btn_reject": "❌ 拒绝申请",
    "btn_broadcast_all": "👥 发送给所有用户",
    "btn_broadcast_vip": "💎 仅VIP用户",
    
    # VIP到期提醒
    "vip_reminder": "⏰ VIP 即将到期提醒\n\n您的 VIP 会员将在 {days} 天后到期\n\n💎 续费价格：{price} USDT / {duration} 天\n\n📍 充值地址 (TRC20)：\n<code>{address}</code>\n\n转账后发送 /deposit 交易哈希 提交申请",
    "vip_expired": "❌ VIP 已过期\n\n您的 VIP 会员已过期，已自动降级为普通用户\n指标配额已恢复为 1 个\n\n💎 重新开通：{price} USDT / {duration} 天\n\n📍 充值地址 (TRC20)：\n<code>{address}</code>\n\n转账后发送 /deposit 交易哈希 提交申请",
    
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