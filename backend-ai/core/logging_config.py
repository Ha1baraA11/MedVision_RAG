# core/logging_config.py
"""
结构化日志配置 + 请求追踪中间件
================================
提供全局 logger 和 TraceMiddleware，供所有模块统一使用。
"""

import time
import uuid
import logging
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


# 请求级 trace_id（ContextVar 保证协程安全）
trace_id_var: ContextVar[str] = ContextVar('trace_id', default='-')


class StructuredFormatter(logging.Formatter):
    """结构化日志格式器，自动注入 trace_id"""
    def format(self, record):
        record.trace_id = trace_id_var.get('-')
        return super().format(record)


# 全局 logger 初始化
_handler = logging.StreamHandler()
_formatter = StructuredFormatter(
    fmt='%(asctime)s | %(levelname)-7s | trace=%(trace_id)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
_handler.setFormatter(_formatter)

logger = logging.getLogger('medvision')
logger.setLevel(logging.INFO)
logger.handlers = [_handler]


class TraceMiddleware(BaseHTTPMiddleware):
    """为每个请求生成唯一 trace_id，自动记录请求耗时"""
    async def dispatch(self, request: Request, call_next):
        tid = uuid.uuid4().hex[:8]
        trace_id_var.set(tid)
        start = time.time()
        logger.info(f">>> {request.method} {request.url.path}")
        response = await call_next(request)
        latency_ms = (time.time() - start) * 1000
        logger.info(f"<<< {request.method} {request.url.path} | status={response.status_code} | latency={latency_ms:.0f}ms")
        return response
