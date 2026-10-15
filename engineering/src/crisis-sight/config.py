# -*- coding: utf-8 -*-
"""读取环境变量配置，不硬编码任何真实密钥。"""

import os

# DeepSeek API Key，未设置时走 demo 模式
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()

# DeepSeek 对话接口（OpenAI 兼容）
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


def llm_enabled():
    """判断是否启用 LLM 模式：设置了 API Key 即为 True。"""
    return bool(DEEPSEEK_API_KEY)