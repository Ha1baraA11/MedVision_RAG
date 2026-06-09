"""
聊天专用模型选择
================
为聊天问答链路提供按请求切换模型的能力，
避免影响 OCR、ASR、Intent 等共用 LLM 单例。
"""

import os
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from core.logging_config import logger

load_dotenv()

# 默认聊天模型：前端未指定或指定非法值时使用
DEFAULT_CHAT_MODEL = "deepseek-v4-flash"
# 支持的聊天模型白名单：前端只能在这些模型中选择
SUPPORTED_CHAT_MODELS = {
    "deepseek-v4-flash",
    "deepseek-v4-pro",
}


def resolve_chat_model_name(requested_model: Optional[str]) -> str:
    """
    解析并校验前端请求的聊天模型名称。

    将前端传入的模型名称转为小写后与白名单匹配，
    不在白名单中的值会降级为默认模型，确保服务稳定性。

    参数:
        requested_model (str | None): 前端请求的模型名称

    返回:
        str: 校验通过的模型名称（小写）
    """
    candidate = (requested_model or "").strip().lower()
    if not candidate:
        return DEFAULT_CHAT_MODEL

    if candidate in SUPPORTED_CHAT_MODELS:
        return candidate

    logger.warning(
        f" Unsupported chat model '{requested_model}', fallback to {DEFAULT_CHAT_MODEL}"
    )
    return DEFAULT_CHAT_MODEL


def build_chat_llm(requested_model: Optional[str]) -> ChatOpenAI:
    """
    按本次请求动态构建聊天用 LLM 实例。

    每次请求独立创建 ChatOpenAI 实例，避免影响 OCR、ASR、Intent 等
    共用的全局 LLM 单例，实现按请求切换模型的能力。

    参数:
        requested_model (str | None): 前端请求的模型名称

    返回:
        ChatOpenAI: 配置好的 LangChain 聊天模型实例
    """
    resolved_model = resolve_chat_model_name(requested_model)
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    logger.info(f" Chat model selected: {resolved_model}")
    return ChatOpenAI(
        model=resolved_model,
        api_key=api_key,
        base_url=base_url,
        temperature=0.3
    )
