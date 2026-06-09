# services/asr.py
"""
语音识别 (ASR) + VAD 门控 + 医学术语纠错
==========================================
Silero VAD 深度学习语音检测、Whisper 转录、LLM 同音字纠错。
"""

import torch

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from core.logging_config import logger
from core.config import llm

# ==========================================
# Silero VAD 模型加载
# ==========================================
# 加载 Silero VAD 深度学习模型，用于高精度语音活动检测（区分人声与静音/噪音）
logger.info(" 加载 Silero VAD 模型（高精度语音检测）...")
try:
    vad_model, _vad_utils = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        force_reload=False,
        trust_repo=True
    )
    (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = _vad_utils
    logger.info(" Silero VAD Model Loaded Successfully.")
except Exception as e:
    # 模型加载失败时降级为无 VAD 模式，所有音频直接放行
    logger.warning(f" Silero VAD 加载失败: {e}，降级为无 VAD 模式。")
    vad_model = None
    get_speech_timestamps = None
    read_audio = None

# ==========================================
# 幻觉黑名单
# ==========================================
HALLUCINATION_BLACKLIST = [
    "作曲", "作词", "字幕", "copyright", "subtitle",
    "amara.org", "bilibili", "优酷", "腾讯视频",
    "by Jonathan Lee", "李宗盛", "张学友"
]


def check_vad_speech(audio_path: str) -> bool:
    """
    使用 Silero VAD 检测音频是否包含人声。

    通过深度学习模型分析音频波形，判断其中是否包含有效人声段落，
    用于在调用 Whisper 转录前过滤掉纯静音或噪音音频，节省 API 调用成本。

    参数:
        audio_path (str): 音频文件路径

    返回:
        bool: True 表示包含人声（放行），False 表示纯静音/噪音（拦截）
    """
    if not vad_model:
        return True

    try:
        wav = read_audio(audio_path)
        speech_timestamps = get_speech_timestamps(wav, vad_model, sampling_rate=16000)

        if len(speech_timestamps) > 0:
            # 计算总人声时长（采样点数 / 采样率 16kHz = 秒数）
            total_speech_duration = sum([(t['end'] - t['start']) for t in speech_timestamps]) / 16000
            logger.info(f" VAD 检测到人声: {total_speech_duration:.2f}秒")
            return True
        else:
            logger.info(" VAD 检测为纯静音/噪音，跳过转录（节省 API 成本）")
            return False
    except Exception as e:
        logger.warning(f" VAD Check Error: {e}")
        return True  # 异常时默认放行，避免误拦截有效音频


def correct_medical_terms(text: str) -> dict:
    """
    使用 LLM 纠正语音识别中的医学同音错别字和幻觉内容。

    处理流程：
    1. 先通过黑名单快速过滤已知的 Whisper 幻觉模式（如字幕、版权信息）
    2. 再调用 LLM 进行同音字纠正（如"阿木西林" -> "阿莫西林"）和语法修正
    3. LLM 判定为幻觉的内容返回空文本

    参数:
        text (str): Whisper 原始转录文本

    返回:
        dict: {"status": "ok"|"hallucination"|"error", "text": "纠正后文本"}
    """
    if not text or len(text) < 2:
        return {"status": "ok", "text": text}

    # 第一层过滤：在调用 LLM 之前，先用黑名单快速检测已知的 Whisper 幻觉模式
    for bad_word in HALLUCINATION_BLACKLIST:
        if bad_word.lower() in text.lower():
            logger.warning(f" Detected Hallucination Pattern: '{bad_word}' in '{text}' -> Filtered.")
            return {"status": "hallucination", "text": ""}

    correction_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个医疗语音纠错专家。用户的输入是语音识别的结果，可能包含同音错别字、语法混乱或完全无关的字幕幻觉。
任务：
1. **识别幻觉**：如果输入文本明显是歌曲信息（如"作曲"、"作词"）、字幕组信息（"Subtitle by"）、版权声明或完全无意义的乱码，请直接输出 "EMPTY"。
2. **纠正医学术语错字**：
   - 阿木西林 -> 阿莫西林
   - 部落粉 -> 布洛芬
   - 头孢可馨 -> 头孢克肟
   - 芬必得 -> 芬必得 (正确)
3. **纠正语音识别导致的语法错误**：语音识别经常把句子听错，需要结合上下文推测用户真实意图。
   - 这叫什么吃 -> 这个药怎么吃
   - 一次吃几里 -> 一次吃几粒
   - 饭前还是饭后吃啊 -> 饭前还是饭后吃
   - 能不能搁一块吃 -> 能不能一起吃
4. **保留原意**：如果句子已经是合理的医疗问题且没有错误，原样输出。

只输出纠正后的完整句子，不要解释。"""),
        ("user", "{text}")
    ])

    try:
        correction_chain = correction_prompt | llm | StrOutputParser()
        corrected = correction_chain.invoke({"text": text})

        # 第二层过滤：检查 LLM 是否判定输入为幻觉（输出 "EMPTY" 表示幻觉）
        if corrected.strip() == "EMPTY":
            logger.info(f" LLM Filtered Hallucination: '{text}' -> EMPTY")
            return {"status": "hallucination", "text": ""}

        return {"status": "ok", "text": corrected.strip()}
    except Exception as e:
        logger.error(f"Correction Error: {e}")
        return {"status": "error", "text": ""}
