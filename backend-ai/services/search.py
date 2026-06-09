# services/search.py
"""
历史药品搜索
==============
调用 Java Backend API 搜索药品库存。
"""

import requests

from core.logging_config import logger


def search_history_medicine(name: str):
    """
    搜索历史药品库存：调用 Java 后端 API 按药品名称模糊搜索。

    当用户意图被识别为"历史查询"时（如"阿莫西林怎么吃"），
    调用此函数从药箱历史记录中查找匹配的药品信息。

    参数:
        name (str): 药品名称关键词（如"阿莫西林"）

    返回:
        dict | None: 匹配到的第一条药品记录（含 id、name、fullText 等字段），未找到返回 None
    """
    try:
        url = f"http://localhost:8080/api/medicine/search?name={name}"
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            # 兼容 Spring Boot 分页响应格式：数据可能在 content 字段中（分页）或直接是数组
            records = data.get("content", data) if isinstance(data, dict) else data
            if records and len(records) > 0:
                return records[0]
        return None
    except Exception as e:
        logger.error(f"Search API Error: {e}")
        return None
