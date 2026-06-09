# models/schemas.py
"""
Pydantic 请求模型
==================
定义所有 API 接口的请求体结构。
"""

from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    context: str
    question: str
    medicine_id: Optional[int] = None      # 用于持久化存储，实现按药品分离的知识库
    medicine_name: Optional[str] = None    # Frontend passed name
    language: str = "zh"                   # Multi-language support
    model: Optional[str] = None            # Per-request chat model selection


class TextAnalysisRequest(BaseModel):
    text: str
