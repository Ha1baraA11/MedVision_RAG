# core/config.py
"""
全局配置与共享单例
==================
集中管理环境变量、LLM / Embedding / Groq 客户端、
文本切分器、临时目录等全局对象。
所有 service 模块从此处导入，避免重复初始化。
"""

import os
from dotenv import load_dotenv

# 加载 .env 环境变量（必须在所有 os.environ.get 之前）
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from groq import Groq

from core.logging_config import logger

# ==========================================
# API Keys
# ==========================================
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ==========================================
# LLM 单例 (DeepSeek)
# ==========================================
llm = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.3
)

# ==========================================
# Groq Client (Whisper ASR)
# ==========================================
groq_client = Groq(api_key=GROQ_API_KEY, timeout=60.0)

# ==========================================
# Embedding Model (BGE-Small-ZH)
# ==========================================
logger.info(" Loading Embedding Model (BAAI/bge-small-zh-v1.5)...")
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    model_kwargs={"local_files_only": True, "device": "cpu"}
)
logger.info(" Embedding Model Loaded.")

# ==========================================
# Text Splitter
# ==========================================
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)

# ==========================================
# 目录常量
# ==========================================
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# ChromaDB 持久化目录 (项目根目录下的 chroma_db/)
# 原 main.py 路径: backend-ai/../chroma_db -> 项目根 chroma_db
_BACKEND_AI_DIR = os.path.dirname(os.path.dirname(__file__))  # backend-ai/
CHROMA_PERSIST_DIR = os.path.join(_BACKEND_AI_DIR, "..", "chroma_db")
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
logger.info(f" ChromaDB 持久化目录: {os.path.abspath(CHROMA_PERSIST_DIR)}")
