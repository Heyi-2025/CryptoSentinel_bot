# -*- coding: utf-8 -*-
"""
国际化工具函数
Internationalization utility functions
"""
from typing import Optional
from locales import ZH_MESSAGES, EN_MESSAGES

LANGUAGES = {
    "zh": ZH_MESSAGES,
    "en": EN_MESSAGES,
}

DEFAULT_LANGUAGE = "zh"


def get_message(key: str, lang: str = "zh", **kwargs) -> str:
    """
    获取多语言消息
    
    Args:
        key: 消息键
        lang: 语言代码 (zh/en)
        **kwargs: 格式化参数
    
    Returns:
        消息文本
    """
    messages = LANGUAGES.get(lang, LANGUAGES[DEFAULT_LANGUAGE])
    text = messages.get(key, key)
    
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def detect_language(language_code: Optional[str]) -> str:
    """
    根据 Telegram language_code 检测语言
    
    Args:
        language_code: Telegram 用户语言代码 (如 "zh-hans", "en", "ru")
    
    Returns:
        语言代码 (zh/en)
    """
    if not language_code:
        return DEFAULT_LANGUAGE
    
    if language_code.lower().startswith("zh"):
        return "zh"
    
    return "en"


def get_button_text(key: str, lang: str = "zh") -> str:
    """
    获取按钮文本
    
    Args:
        key: 按钮键 (如 "btn_confirm", "btn_cancel")
        lang: 语言代码
    
    Returns:
        按钮文本
    """
    return get_message(key, lang)