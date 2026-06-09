# services/tts.py
"""
文本转语音 (TTS)
=================
使用 Edge TTS 生成高质量中文语音。
"""

import os
import time
import uuid
import asyncio

import edge_tts

from core.logging_config import logger
from core.config import TEMP_DIR

# TTS 音频缓存配置
CACHE_TTL = 60          # 缓存有效期（秒）：相同文本在此时间内直接返回缓存文件
TTS_TIMEOUT = 15        # edge-tts 生成超时（秒）：超过此时间视为生成失败
MIN_FILE_SIZE = 100     # 最小有效文件大小（字节）：防止读到未写完的空文件


async def generate_tts(text: str) -> str:
    """
    生成 TTS 音频文件，返回文件路径。
    优先命中磁盘缓存（<CACHE_TTL 秒内），否则实时生成。
    使用临时文件 + 原子重命名，避免竞态条件读到未完成的文件。
    """
    # 使用微软 Edge TTS 的云晰语音（zh-CN-YunxiNeural），音质较好
    voice = "zh-CN-YunxiNeural"
    # 以文本哈希值作为文件名，实现相同文本的缓存复用
    output_file = os.path.join(TEMP_DIR, f"tts_{hash(text)}.mp3")

    # 缓存命中判断：文件存在 + 未超过有效期 + 文件大小正常 -> 直接返回缓存路径
    if os.path.exists(output_file) and (time.time() - os.path.getmtime(output_file)) < CACHE_TTL:
        file_size = os.path.getsize(output_file)
        if file_size >= MIN_FILE_SIZE:
            logger.info(f" TTS 缓存命中: {output_file} ({file_size}bytes)")
            return output_file
        else:
            logger.warning(f" TTS 缓存文件过小({file_size}bytes)，重新生成: {output_file}")

    # 使用临时文件 + 原子重命名策略：先写入 .tmp 文件，完成后通过 os.replace 原子替换
    # 这样并发的同步请求不会读到写了一半的文件
    tmp_file = output_file + f".{uuid.uuid4().hex[:8]}.tmp"
    communicate = edge_tts.Communicate(text, voice)
    try:
        await asyncio.wait_for(communicate.save(tmp_file), timeout=TTS_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error(f" TTS 生成超时 ({TTS_TIMEOUT}s): {text[:50]}...")
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        raise

    # 校验临时文件：确保生成成功且文件大小有效，然后原子重命名为最终文件
    if not os.path.exists(tmp_file) or os.path.getsize(tmp_file) < MIN_FILE_SIZE:
        logger.error(f" TTS 生成失败：临时文件不存在或过小: {tmp_file}")
        raise RuntimeError(f"TTS generation failed: temp file missing or too small")
    os.replace(tmp_file, output_file)
    logger.info(f" TTS 生成完成: {output_file} ({os.path.getsize(output_file)}bytes)")
    return output_file
