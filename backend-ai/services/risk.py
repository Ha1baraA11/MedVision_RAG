# services/risk.py
"""
风险关键词检测 + TTL 缓存
==========================
从 MySQL 动态加载风险关键词，带 60 秒 TTL 缓存减少数据库压力。
"""

import os
import time
import json
import pymysql

from core.logging_config import logger

# 风险关键词 TTL 缓存
_risk_cache = {"keywords": None, "expires_at": 0}
RISK_CACHE_TTL = 60  # 缓存有效期 60 秒


def get_db_connection():
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DATABASE", "medvision"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


def load_risk_keywords() -> list:
    """从 MySQL 加载动态配置的风险关键词"""
    default_keywords = ["副作用", "过敏", "禁忌", "禁用", "不良反应", "慎用", "忌用", "自杀", "服用过量"]
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT config_value FROM system_config WHERE config_key = 'risk_keywords'"
            cursor.execute(sql)
            result = cursor.fetchone()
            if result and result['config_value']:
                try:
                    # Parse JSON: {"keywords": [...], "updated_at": ...}
                    data = json.loads(result['config_value'])
                    if isinstance(data, dict) and 'keywords' in data:
                        return data['keywords']
                except json.JSONDecodeError:
                    # Fallback for old legacy format (comma string)
                    val_str = result['config_value'].replace('，', ',')
                    return [k.strip() for k in val_str.split(',') if k.strip()]
    except Exception as e:
        logger.warning(f" DB Config Load Error: {e}. Using defaults.")

    return default_keywords


def check_risk_keywords(text: str) -> list:
    """检测文本中的风险关键词（带 TTL 缓存，减少数据库压力）"""
    now = time.time()
    if _risk_cache["keywords"] is None or now > _risk_cache["expires_at"]:
        _risk_cache["keywords"] = load_risk_keywords()
        _risk_cache["expires_at"] = now + RISK_CACHE_TTL
        logger.info(f"风险词缓存刷新 | count={len(_risk_cache['keywords'])} | ttl={RISK_CACHE_TTL}s")

    current_keywords = _risk_cache["keywords"]
    found = [kw for kw in current_keywords if kw in str(text)]
    return found
