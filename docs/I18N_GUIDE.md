# Bot 国际化改造指南

## 1. 修改导入部分

在 `bot.py` 顶部添加：

```python
from i18n import get_message, detect_language, get_button_text
from db_manager import get_user_language, set_user_language
```

## 2. 添加获取用户语言的辅助函数

```python
async def get_lang(update: Update) -> str:
    """获取用户的语言设置"""
    if not update.effective_user:
        return "zh"
    
    uid = update.effective_user.id
    
    # 先从数据库获取
    lang = await get_user_language(uid)
    if lang:
        return lang
    
    # 使用 Telegram 自动检测
    lang_code = update.effective_user.language_code
    return detect_language(lang_code)
```

## 3. 修改各个命令函数

### 示例：修改 start 函数

**原代码：**
```python
await safe_reply(
    update,
    "📈 CryptoSentinel 监控系统\n\n请选择交易所：",
    reply_markup=reply_markup
)
```

**新代码：**
```python
lang = await get_lang(update)
await safe_reply(
    update,
    get_message("welcome", lang),
    reply_markup=reply_markup
)
```

## 4. 添加 /language 命令

```python
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """切换语言"""
    lang = await get_lang(update)
    
    keyboard = [
        [InlineKeyboardButton(
            get_button_text("btn_lang_zh", lang), 
            callback_data="lang_zh"
        )],
        [InlineKeyboardButton(
            get_button_text("btn_lang_en", lang), 
            callback_data="lang_en"
        )],
    ]
    
    await safe_reply(
        update,
        get_message("language_select", lang),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理语言选择"""
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    uid = update.effective_user.id
    new_lang = query.data.split("_")[-1]  # "zh" or "en"
    
    await set_user_language(uid, new_lang)
    
    await query.edit_message_text(
        get_message("language_changed", new_lang)
    )
```

## 5. 在 main() 中注册命令

```python
application.add_handler(CommandHandler("language", language_command))
application.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
```

## 6. 修改按钮文本

**原代码：**
```python
keyboard = [
    [InlineKeyboardButton("✅ 确认", callback_data="confirm")],
    [InlineKeyboardButton("❌ 取消", callback_data="cancel")]
]
```

**新代码：**
```python
lang = await get_lang(update)
keyboard = [
    [InlineKeyboardButton(
        get_button_text("btn_confirm", lang), 
        callback_data="confirm"
    )],
    [InlineKeyboardButton(
        get_button_text("btn_cancel", lang), 
        callback_data="cancel"
    )]
]
```

## 7. 需要修改的主要函数列表

| 函数名 | 需要改动的位置 |
|--------|---------------|
| `start` | 欢迎文字、订阅上限提示 |
| `symbol_received` | 格式错误提示 |
| `timeframe_callback` | 时间周期选择提示 |
| `indicator_callback` | 指标选择提示、确认文字 |
| `confirm_callback` | 保存成功/失败提示 |
| `list_subs` | 订阅列表标题、空列表提示 |
| `delete_sub` | 删除成功/失败提示 |
| `donate` | 打赏地址显示 |
| `admin_panel` | 管理员面板文字 |
| `button_callback` | 各种按钮回显文字 |

## 8. 按钮文本对照表

| 原文本 | 键名 |
|--------|------|
| "✅ 确认" | `btn_confirm` |
| "❌ 取消" | `btn_cancel` |
| "⬅️ 返回" | `admin_btn_back` |
| "📢 群发消息" | `admin_btn_broadcast` |
| "📊 统计信息" | `admin_btn_stats` |
| "🇨🇳 中文" | `btn_lang_zh` |
| "🇺🇸 English" | `btn_lang_en` |

## 9. 快速替换方法

由于改动点较多，建议使用以下方式：

1. 在每个函数开头添加 `lang = await get_lang(update)`
2. 将硬编码的中文字符串替换为 `get_message("key", lang)`
3. 将按钮文本替换为 `get_button_text("btn_key", lang)`
4. 使用 `**kwargs` 传递动态参数：`get_message("key", lang, name="BTC")`

## 10. 测试

修改完成后，测试以下场景：

1. 发送 `/language` 切换语言
2. 发送 `/start` 验证欢迎文字
3. 发送 `/donate` 验证打赏地址显示
4. 发送 `/admin` 验证管理员面板

---

*文档版本: 3.0*
*最后更新: 2026-04-08*