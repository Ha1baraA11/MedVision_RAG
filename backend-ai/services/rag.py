# services/rag.py
"""
自适应 RAG 检索 + 问答
========================
根据文本长度自动选择 Context Stuffing 或 Vector RAG，
支持中英双语 Prompt。
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma

from core.logging_config import logger
from core.config import embedding_model, text_splitter, CHROMA_PERSIST_DIR
from services.chat_model import build_chat_llm

# ==========================================
# RAG Prompt 模板（中文版 + 英文版）
# 根据用户选择的语言切换对应的提示词
# ==========================================
rag_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个视障人士的用药助手。这非常重要：
1. **书面语转口语**：你的回答将被直接朗读。**绝对禁止**使用任何Markdown符号（如 *、#、-）。
2. **ASR拼音纠错**：用户的提问是语音识别生成的，错字率极高。请尝试**将输入文本转换为拼音**，然后匹配最可能的医学问题。
   - 例："怎么池" (zen me chi) -> 推测为 "怎么吃"
   - 例："依此吃几粒" (yi ci chi ji li) -> 推测为 "一次吃几粒"
   - 例："福作用" -> "副作用"
3. **纯文本输出**：不要分段，不要列表。用逗号和句号连接自然的口语段落。
4. **基于事实**：严格基于OCR内容回答。
6. **双语结构化卡片（隐藏指令）**：如果问题涉及"用法"、"用量"、"禁忌"、"副作用"：
   请在回答的**最后**（必须是最后），附加一个严格的 JSON 数据块（不要Markdown，不要代码块），被 <card> 标签包裹。必须包含中英文双语信息：
   <card>
   {{
       "name_zh": "药品名称 (中文)",
       "name_en": "Medicine Name (English)",
       "usage_zh": "用法简述 (中文)",
       "usage_en": "Usage summary (English)",
       "taboo_zh": "核心禁忌 (中文)",
       "taboo_en": "Core contraindications (English)"
   }}
   </card>"""),
    ("user", "说明书内容: {context}\n用户语音提问: {question}")
])

# 英文版 Prompt 模板
rag_prompt_en = ChatPromptTemplate.from_messages([
    ("system", """You are MedVision, a helpful assistant for visually impaired users.
1. **Spoken Style**: Your answer will be read out loud. Do NOT use Markdown (no *, #, -).
2. **ASR Correction**: The user input is from speech recognition. Try to guess the correct medical terms.
3. **Plain Text**: Use natural paragraphs with commas and periods.
4. **Fact-based**: Strictly based on the OCR context.
5. **Bilingual Structured Card (Hidden)**: If the question asks about "Usage", "Dosage", "Contraindications", "Side Effects":
   At the VERY END, append a strict JSON block (no Markdown) wrapped in <card> tags. MUST include both Chinese and English:
   <card>
   {{
       "name_zh": "Medicine Name (Chinese)",
       "name_en": "Medicine Name (English)",
       "usage_zh": "Usage summary (Chinese)",
       "usage_en": "Usage summary (English)",
       "taboo_zh": "Core contraindications (Chinese)",
       "taboo_en": "Core contraindications (English)"
   }}
   </card>"""),
    ("user", "Context: {context}\nQuestion: {question}")
])


def smart_rag_search(full_text: str, user_question: str, medicine_id: int = None) -> tuple:
    """
    自适应 RAG 检索：根据文本长度自动选择最优检索策略。

    策略 A（短文本 < 1500字）：直接将全文作为上下文交给 LLM（Context Stuffing），精度最高。
    策略 B（长文本 >= 1500字）：切片后存入 ChromaDB 向量库，语义检索 Top 3 相关片段。

    参数:
        full_text (str): OCR 提取的药品说明书全文
        user_question (str): 用户的提问文本
        medicine_id (int, optional): 药品 ID，用于向量库按药品隔离存储

    返回:
        tuple: (context_str, citations_list)
            - context_str: 拼接后的上下文文本
            - citations_list: 引用列表（仅向量检索模式下非空），每项含 index/content/score
    """
    # 策略 A: 短文本直接全量阅读（Context Stuffing），精度最高
    if len(full_text) < 1500:
        logger.info(f" 文本较短 ({len(full_text)}字)，采用全量阅读模式 (High Accuracy)")
        return full_text, []

    # 策略 B: 长文本走向量检索流水线（Vector RAG）
    logger.info(f" 文本过长 ({len(full_text)}字)，启动向量检索模式 (RAG Pipeline)")

    try:
        # 1. 使用 text_splitter 将长文本切分为语义片段
        docs = [Document(page_content=t) for t in text_splitter.split_text(full_text)]

        # 2. 将文档片段嵌入向量并持久化存入 ChromaDB
        collection_name = f"medicine_{medicine_id}" if medicine_id else "default_collection"

        persistent_db = Chroma.from_documents(
            docs,
            embedding_model,
            collection_name=collection_name,
            persist_directory=CHROMA_PERSIST_DIR,
            collection_metadata={"hnsw:space": "cosine"}
        )
        logger.info(f" 向量已持久化到: {CHROMA_PERSIST_DIR}, collection: {collection_name}")

        # 3. 语义检索：返回与用户问题最相关的 Top 3 片段及其相似度分数
        results_with_scores = persistent_db.similarity_search_with_score(user_question, k=3)

        # 4. 拼接检索结果为上下文字符串，同时构建引用列表供前端展示
        chunks = []
        citations = []
        for i, (doc, score) in enumerate(results_with_scores, start=1):
            chunks.append(doc.page_content)
            # ChromaDB 余弦距离: 0=完全相同, 2=完全不同; 转换为相似度百分比
            similarity = max(0.0, 1.0 - score)
            citations.append({
                "index": i,
                "content": doc.page_content[:200],
                "score": round(similarity, 2)
            })

        rag_context = "\n...\n".join(chunks)
        logger.info(f" RAG 检索完成，提取了关键上下文: {len(rag_context)}字, 引用数: {len(citations)}")
        return rag_context, citations

    except Exception as e:
        logger.warning(f"Vector RAG Error: {e}, falling back to full text.")
        return full_text[:4000], []


def run_rag(ocr_context: str, user_question: str, language: str = "zh", model: str = None) -> str:
    """
    执行 RAG 问答链：将上下文和用户问题交给 LLM 生成回答。

    根据 language 参数选择中文或英文 Prompt 模板，
    根据 model 参数选择不同的聊天模型实例。

    参数:
        ocr_context (str): 经过检索的药品说明书上下文
        user_question (str): 用户的提问文本
        language (str): 回答语言，"zh" 中文 / "en" 英文
        model (str, optional): 前端指定的模型名称

    返回:
        str: LLM 生成的回答文本（已去除 Markdown 符号）
    """
    try:
        # 根据语言选择 Prompt 模板，根据 model 参数构建对应的 LLM 实例
        selected_prompt = rag_prompt_en if language == "en" else rag_prompt
        chat_llm = build_chat_llm(model)
        # 构建 LangChain 处理链：Prompt -> LLM -> 字符串输出解析
        chain = selected_prompt | chat_llm | StrOutputParser()

        clean_content = chain.invoke({
            "context": ocr_context,
            "question": user_question
        })
        # 后处理：移除 LLM 可能残留的 Markdown 符号，确保输出为纯文本（便于 TTS 朗读）
        return clean_content.replace("*", "").replace("#", "").strip()
    except Exception as e:
        logger.error(f"LangChain RAG Error: {e}")
        return "Sorry, AI service is unavailable." if language == "en" else "抱歉，AI 服务暂时不可用。"
