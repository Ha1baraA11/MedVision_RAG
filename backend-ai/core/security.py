# core/security.py
"""
内部接口鉴权
=============
FastAPI 依赖注入函数，校验 X-Internal-Token 请求头。
"""

import os
from typing import Optional
from fastapi import Header, HTTPException

INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "")


async def verify_internal_token(x_internal_token: Optional[str] = Header(None)):
    """校验内部服务间调用的 Token，防止未授权访问"""
    if not INTERNAL_TOKEN:
        return  # Token 未配置时跳过校验（开发模式）
    if x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid internal token")
