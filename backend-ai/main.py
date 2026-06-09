# main.py
"""
MedVision AI Service — 薄路由层
================================
所有业务逻辑已拆分至 services/ 模块，
此文件仅负责 FastAPI 初始化、中间件注册和路由编排。
"""

import os
import re
import time
import shutil
import uuid
import asyncio

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# 数据清洗工具（毕设亮点: 脏数据清洗）
from unstructured.cleaners.core import (
    clean_bullets,
    group_broken_paragraphs
)

# --- 核心模块 ---
from core.logging_config import logger, TraceMiddleware
from core.config import TEMP_DIR, groq_client
from core.security import verify_internal_token

# --- 数据模型 ---
from models.schemas import ChatRequest, TextAnalysisRequest

# --- 业务服务 ---
from services.ocr import (
    run_ocr,
    extract_medicine_name,
    extract_text_from_pdf,
    extract_text_from_docx,
)
from services.asr import check_vad_speech, correct_medical_terms
from services.rag import smart_rag_search, run_rag
from services.email import send_risk_email
from services.risk import check_risk_keywords
from services.intent import analyze_intent
from services.search import search_history_medicine
from services.tts import generate_tts


# ==========================================
# HEIC/HEIF 格式转换（iPhone 拍照默认格式）
# ==========================================
def _convert_heic_to_jpeg(image_path: str) -> str:
    """
    检测 HEIC/HEIF 格式并转换为 JPEG，返回转换后的文件路径（或原路径）。
    iPhone 拍照默认使用 HEIC 格式，OCR 引擎无法直接识别，需要先转换为 JPEG。

    参数:
        image_path (str): 原始图片文件路径

    返回:
        str: 转换后的 JPEG 文件路径；若非 HEIC 格式或转换失败，返回原路径
    """
    try:
        from PIL import Image
        import pillow_heif

        # 读取文件头部检测 HEIC 签名
        with open(image_path, "rb") as f:
            header = f.read(12)

        # HEIC/HEIF 文件的 ftyp 签名
        is_heic = b"ftyp" in header and (b"heic" in header or b"heix" in header or b"mif1" in header)

        if not is_heic:
            return image_path

        logger.info(f" Detected HEIC/HEIF format, converting to JPEG...")
        heif_file = pillow_heif.read_heif(image_path)
        img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")

        jpeg_path = image_path.rsplit(".", 1)[0] + "_converted.jpg"
        img.save(jpeg_path, "JPEG", quality=95)
        logger.info(f" Converted HEIC → JPEG: {jpeg_path}")
        return jpeg_path
    except Exception as e:
        logger.warning(f" HEIC conversion failed: {e}, trying original file")
        return image_path


# ==========================================
# FastAPI 应用初始化
# ==========================================
app = FastAPI(title="MedVision AI Service (LangChain Edition)")

# CORS 跨域白名单：只允许本地开发端口访问
CORS_ORIGINS = [
    "http://localhost:5174",
    "http://localhost:8080",
    "http://localhost:8501",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8501",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求追踪中间件
app.add_middleware(TraceMiddleware)


# ==========================================
# 路由: GET /health
# ==========================================
@app.get("/health")
async def health_check():
    """
    健康检查端点：供启动脚本和负载均衡器探测服务是否就绪。

    返回:
        dict: {"status": "ok"} 表示服务正常运行
    """
    return {"status": "ok"}


# ==========================================
# 路由: POST /internal/ocr
# ==========================================
@app.post("/internal/ocr", dependencies=[Depends(verify_internal_token)])
async def api_ocr(file: UploadFile = File(...)):
    """
    OCR 识别接口：接收图片/PDF/Word 文件，返回识别出的文本和提取的药名。

    参数:
        file (UploadFile): 上传的文件，支持图片（含 HEIC）、PDF、Word 格式

    返回:
        dict: {"text": "清洗后的文本", "name": "提取的药品名称"}
    """
    _, ext = os.path.splitext(file.filename)
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    temp_path = os.path.join(TEMP_DIR, safe_filename)

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(temp_path)
    logger.info(f" Received file {file.filename}, saved safely to {temp_path}, file size: {file_size} bytes")

    start_time = time.time()
    try:
        filename_lower = file.filename.lower()
        logger.info(f" Processing file: {filename_lower}")

        raw_text = ""

        # 1. PDF 文件处理：提取 PDF 中的文本内容
        if filename_lower.endswith(".pdf"):
            raw_text = extract_text_from_pdf(temp_path)

        # 2. Word 文件处理：提取 .docx/.doc 中的文本内容
        elif filename_lower.endswith(".docx") or filename_lower.endswith(".doc"):
            raw_text = extract_text_from_docx(temp_path)

        # 3. 图片文件处理（默认走 OCR 识别）
        else:
            # HEIC/HEIF 格式检测与转换（iPhone 拍照默认格式）
            temp_path = _convert_heic_to_jpeg(temp_path)
            raw_text = run_ocr(temp_path)

        logger.info(f" Raw OCR output preview (first 300 chars): {raw_text[:300]}")
        logger.info(f" Raw OCR total length: {len(raw_text)} chars")

        # 数据清洗（保留段落结构，不压缩换行）
        cleaned_text = group_broken_paragraphs(raw_text)
        cleaned_text = clean_bullets(cleaned_text)
        cleaned_text = re.sub(r"[\xa0]", " ", cleaned_text)       # 仅替换 &nbsp;
        cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)       # 压缩水平空白
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)    # 多个连续换行 → 双换行段落分隔
        cleaned_text = cleaned_text.strip()

        logger.info(f" Data Cleaning: {len(raw_text)} chars -> {len(cleaned_text)} chars")

        med_name = extract_medicine_name(cleaned_text)

        logger.info(f" OCR Success. Time: {time.time() - start_time:.2f}s")
        logger.info(f" Extracted Name: {med_name}")

        return {"text": cleaned_text, "name": med_name}
    except Exception as e:
        logger.error(f"OCR Error: {e}")
        return {"text": "", "name": "未知药品"}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ==========================================
# 路由: POST /internal/analyze_text
# ==========================================
@app.post("/internal/analyze_text", dependencies=[Depends(verify_internal_token)])
async def api_analyze_text(req: TextAnalysisRequest):
    """
    文本分析接口：接收用户手动输入的文本，清洗后提取药名。

    参数:
        req (TextAnalysisRequest): 包含用户输入文本的请求体

    返回:
        dict: {"text": "清洗后的文本", "name": "提取的药品名称"}
    """
    start_time = time.time()
    try:
        raw_text = req.text

        cleaned_text = group_broken_paragraphs(raw_text)
        cleaned_text = clean_bullets(cleaned_text)
        cleaned_text = re.sub(r"[\xa0]", " ", cleaned_text)
        cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
        cleaned_text = cleaned_text.strip()

        logger.info(f" Manual Text Cleaning: {len(raw_text)} chars -> {len(cleaned_text)} chars")

        med_name = extract_medicine_name(cleaned_text)

        logger.info(f" Text Analysis Success. Time: {time.time() - start_time:.2f}s")
        logger.info(f" Extracted Name: {med_name}")

        return {"text": cleaned_text, "name": med_name}
    except Exception as e:
        logger.error(f"Text Analysis Error: {e}")
        return {"text": "", "name": "未知药品"}


# ==========================================
# 路由: POST /internal/transcribe
# ==========================================
@app.post("/internal/transcribe", dependencies=[Depends(verify_internal_token)])
async def api_transcribe(file: UploadFile = File(...)):
    """
    语音转录接口：接收录音文件，经 VAD 门控过滤静音后，调用 Whisper V3 转录，再用 LLM 纠正医学术语。

    参数:
        file (UploadFile): 上传的音频文件

    返回:
        dict: {"status": "状态标识", "text": "纠错后文本", "raw": "Whisper 原始转录文本"}
    """
    temp_path = os.path.join(TEMP_DIR, f"audio_{int(time.time())}_{file.filename}")
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    start_time = time.time()
    try:
        # 步骤 0：VAD 门控 —— 使用 Silero VAD 检测音频是否包含人声，过滤纯静音/噪音
        is_speech = check_vad_speech(temp_path)
        if not is_speech:
            logger.info(" VAD Gating: Blocked Silent Audio.")
            return {"status": "silence", "text": "", "raw": "[VAD] Silence Filtered"}

        # 步骤 1：调用 Groq Whisper V3 进行语音转文字
        with open(temp_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(temp_path, audio_file.read()),
                model="whisper-large-v3",
                prompt="请准确识别医学名词，如阿莫西林、布洛芬、头孢克肟等。",
                response_format="json",
                language="zh",
                temperature=0.0
            )

        raw_text = transcription.text
        logger.info(f" Whisper Raw: {raw_text}")

        # 步骤 2：使用 LLM 纠正语音识别中的医学同音错别字（如"阿木西林" -> "阿莫西林"）
        correction_result = correct_medical_terms(raw_text)
        corrected_text = correction_result.get("text", "")
        status = correction_result.get("status", "ok")

        logger.info(
            f" Corrected: {corrected_text} | status={status} "
            f"(Total Time: {time.time() - start_time:.2f}s)"
        )
        return {"status": status, "text": corrected_text, "raw": raw_text}

    except Exception as e:
        logger.error(f"ASR Error: {e}")
        return {"status": "error", "text": "", "raw": "", "error": str(e)}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ==========================================
# 路由: POST /internal/chat
# ==========================================
@app.post("/internal/chat", dependencies=[Depends(verify_internal_token)])
async def api_chat(req: ChatRequest):
    """
    智能问答接口：接收用户问题和 OCR 上下文，经过意图识别、RAG 检索后生成回答。
    支持历史药品查询切换、风险关键词预警邮件、TTS 音频预生成。

    参数:
        req (ChatRequest): 包含问题、上下文、药品ID、语言、模型等信息的请求体

    返回:
        dict: {"answer": "AI 回答文本", "citations": "引用列表（向量检索模式下）"}
    """
    start_time = time.time()
    logger.info(
        f"Chat Request | medicine_id={req.medicine_id} | lang={req.language} "
        f"| model={req.model or 'default'} | q={req.question[:50]}"
    )

    # --- 意图路由：判断用户是查询当前药品还是历史药品 ---
    intent = analyze_intent(req.question)

    current_context = req.context
    current_med_id = req.medicine_id

    if intent.get("type") == "HISTORY" and intent.get("entity"):
        logger.info(f" Detected History Query for: {intent['entity']}")
        history_med = search_history_medicine(intent["entity"])
        if history_med:
            logger.info(f" Found History Medicine: {history_med.get('name')} (ID: {history_med.get('id')})")
            current_context = history_med.get("fullText", "")
            current_med_id = history_med.get("id")
            yield_prefix = f"（已为您切换到历史记录中的：{history_med.get('name')}）\n"
        else:
            logger.info(f" History Medicine Not Found: {intent['entity']}")
            return {"answer": f"抱歉，您的药箱历史里没有找到叫\u201c{intent['entity']}\u201d的药。"}
    else:
        yield_prefix = ""

    # --- 自适应 RAG 检索：根据文本长度自动选择全量阅读或向量检索 ---
    best_context, citations = smart_rag_search(current_context, req.question, current_med_id)

    answer = run_rag(best_context, req.question, req.language, req.model)
    latency = time.time() - start_time
    logger.info(f"Chat Answered | medicine_id={current_med_id} | latency={latency:.2f}s")

    # --- 风险预警检测 ---
    risk_found = check_risk_keywords(req.question)

    if risk_found:
        medicine_name = req.medicine_name or "未知药品"
        if medicine_name == "未知药品" and req.context:
            medicine_name = req.context[:50] + "..."

        logger.warning(f" 检测到风险关键词: {risk_found}，正在发送邮件预警...")
        clean_answer = re.sub(r'<card>[\s\S]*?</card>', '', answer).strip()
        send_risk_email(medicine_name, req.question, clean_answer, risk_found)

    final_answer = yield_prefix + answer

    # TTS 预生成：后台异步生成音频缓存，不阻塞 chat 响应
    try:
        asyncio.create_task(generate_tts(final_answer))
    except Exception:
        pass  # 预生成失败不影响主流程

    return {"answer": final_answer, "citations": citations}


# ==========================================
# 路由: GET /internal/tts
# ==========================================
@app.get("/internal/tts", dependencies=[Depends(verify_internal_token)])
async def api_tts(text: str):
    """
    TTS 语音接口：接收文本，生成 TTS 语音音频文件并返回。

    参数:
        text (str): 需要转换为语音的文本内容

    返回:
        FileResponse: MP3 音频文件的流式响应
    """
    try:
        output_file = await generate_tts(text)
        return FileResponse(output_file, media_type="audio/mpeg", filename="tts.mp3")
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 应用入口：使用 uvicorn 启动 FastAPI 服务
# ==========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
