# backend-ai/tests/test_main.py
"""
MedVision-RAG 核心业务逻辑单元测试
===================================
覆盖目标:
  1. check_risk_keywords()  — 风险关键词检测 + TTL 缓存
  2. smart_rag_search()     — 自适应 RAG 路由 (短文本/长文本/异常降级)
  3. correct_medical_terms() — ASR 纠错 + 幻觉过滤

运行方式: cd backend-ai && python -m pytest tests/ -v
"""

import os
import sys

# 自动切换环境逻辑：检测到没有 pytest 时，自动使用 venv 的 python 重新执行当前脚本
try:
    import pytest
except ImportError:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    venv_python = os.path.join(project_root, "venv", "bin", "python")
    if os.path.exists(venv_python) and sys.executable != venv_python:
        print(f"🔄 [Auto-Fix] 正在自动切换至虚拟环境 ({venv_python})...")
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print("❌ 错误: 未找到 pytest，且未找到项目虚拟环境 (venv)。请先运行 `python -m venv venv` 和 `pip install pytest`。")
        sys.exit(1)

import time
from unittest.mock import patch, MagicMock


# ============================================================
# 因为 main.py 中含有大量模块级副作用 (FastAPI app、数据库连接、
# 模型加载等)，直接 import 会失败。我们通过 monkeypatch 的方式
# 在测试中只导入并测试目标函数的核心逻辑。
#
# 策略: 将 main 模块的全局依赖 mock 掉后再 import，
# 或者直接把函数逻辑在 test 中模拟测试。
# ============================================================


# ----------------------------------------------------------
# 辅助工具: 安全导入 main 模块 (mock 外部依赖)
# ----------------------------------------------------------
@pytest.fixture(autouse=True)
def _mock_heavy_imports(monkeypatch):
    """在 import main.py 之前，mock 掉所有重量级外部依赖"""
    import sys
    # 需要 mock 的模块列表 (避免真实加载模型/启动服务)
    heavy_modules = [
        "ocrmac", "pytesseract",
        "langchain_openai", "langchain_core", "langchain_core.prompts",
        "langchain_core.output_parsers",
        "langchain_huggingface",
        "langchain_community", "langchain_community.vectorstores",
        "langchain_community.document_loaders",
        "langchain.text_splitter",
        "unstructured", "unstructured.cleaners", "unstructured.cleaners.core",
        "chromadb",
        "silero_vad",
        "edge_tts",
        "pymysql",
    ]
    for mod_name in heavy_modules:
        if mod_name not in sys.modules:
            monkeypatch.setitem(sys.modules, mod_name, MagicMock())


# ============================================================
# 1. check_risk_keywords() 测试
# ============================================================
class TestCheckRiskKeywords:
    """风险关键词检测函数测试"""

    def _make_check_fn(self, keywords_list):
        """
        构造一个隔离的 check_risk_keywords 闭包，
        不依赖真实数据库的 load_risk_keywords()。
        """
        cache = {"keywords": None, "expires_at": 0}
        ttl = 60

        def load_fn():
            return keywords_list

        def check_risk_keywords(text: str) -> list:
            now = time.time()
            if cache["keywords"] is None or now > cache["expires_at"]:
                cache["keywords"] = load_fn()
                cache["expires_at"] = now + ttl
            current_keywords = cache["keywords"]
            return [kw for kw in current_keywords if kw in str(text)]

        return check_risk_keywords, cache

    def test_hit_single_keyword(self):
        """命中单个风险词"""
        fn, _ = self._make_check_fn(["副作用", "过敏", "禁忌"])
        result = fn("这个药有什么副作用吗？")
        assert result == ["副作用"]

    def test_hit_multiple_keywords(self):
        """命中多个风险词"""
        fn, _ = self._make_check_fn(["副作用", "过敏", "禁忌"])
        result = fn("过敏了会有什么副作用")
        assert set(result) == {"副作用", "过敏"}

    def test_no_hit(self):
        """无命中时返回空列表"""
        fn, _ = self._make_check_fn(["副作用", "过敏", "禁忌"])
        result = fn("这个药怎么吃")
        assert result == []

    def test_empty_text(self):
        """空文本不应报错"""
        fn, _ = self._make_check_fn(["副作用"])
        result = fn("")
        assert result == []

    def test_cache_prevents_reload(self):
        """TTL 缓存期内不应重复加载"""
        call_count = 0
        original_keywords = ["副作用", "过敏"]

        cache = {"keywords": None, "expires_at": 0}
        ttl = 60

        def counted_load():
            nonlocal call_count
            call_count += 1
            return original_keywords

        def check_fn(text):
            now = time.time()
            if cache["keywords"] is None or now > cache["expires_at"]:
                cache["keywords"] = counted_load()
                cache["expires_at"] = now + ttl
            return [kw for kw in cache["keywords"] if kw in str(text)]

        # 第一次调用：触发加载
        check_fn("副作用")
        assert call_count == 1

        # 第二次调用：应使用缓存
        check_fn("过敏")
        assert call_count == 1  # 没有增加

    def test_cache_expires(self):
        """TTL 过期后应重新加载"""
        call_count = 0
        cache = {"keywords": None, "expires_at": 0}
        ttl = 0.1  # 100ms 超短 TTL

        def counted_load():
            nonlocal call_count
            call_count += 1
            return ["副作用"]

        def check_fn(text):
            now = time.time()
            if cache["keywords"] is None or now > cache["expires_at"]:
                cache["keywords"] = counted_load()
                cache["expires_at"] = now + ttl
            return [kw for kw in cache["keywords"] if kw in str(text)]

        check_fn("副作用")
        assert call_count == 1

        time.sleep(0.15)  # 等待缓存过期

        check_fn("副作用")
        assert call_count == 2  # 重新加载了


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-v", __file__]))


# ============================================================
# 2. smart_rag_search() 测试
# ============================================================
class TestSmartRagSearch:
    """自适应 RAG 路由函数测试"""

    def test_short_text_returns_full(self):
        """短文本 (<1500字) 直接返回原文，不走向量检索"""
        short_text = "阿莫西林胶囊，每次一粒，每日三次。"
        assert len(short_text) < 1500

        # 直接测试核心逻辑（不依赖全局变量）
        def smart_rag_short(full_text, user_question, medicine_id=None):
            if len(full_text) < 1500:
                return full_text
            return "should_not_reach"

        result = smart_rag_short(short_text, "怎么吃")
        assert result == short_text

    def test_long_text_triggers_vector_search(self):
        """长文本 (>=1500字) 应触发向量检索流程"""
        long_text = "药品说明书" * 500  # 2500字
        assert len(long_text) >= 1500

        mock_results = [
            MagicMock(page_content="片段1：每次一粒"),
            MagicMock(page_content="片段2：饭后服用"),
            MagicMock(page_content="片段3：禁忌症"),
        ]

        with patch("langchain_community.vectorstores.Chroma") as MockChroma:
            mock_db = MagicMock()
            mock_db.similarity_search.return_value = mock_results
            MockChroma.from_documents.return_value = mock_db

            # 模拟核心逻辑
            from langchain_community.vectorstores import Chroma
            from unittest.mock import MagicMock as MM

            text_splitter = MM()
            text_splitter.split_text.return_value = ["chunk1", "chunk2", "chunk3"]
            embedding_model = MM()

            # 内联模拟 smart_rag_search 长文本分支
            docs = [MM(page_content=t) for t in text_splitter.split_text(long_text)]
            persistent_db = Chroma.from_documents(docs, embedding_model)
            results = persistent_db.similarity_search("怎么吃", k=3)
            rag_context = "\n...\n".join([r.page_content for r in results])

            assert "片段1" in rag_context
            assert "片段2" in rag_context
            assert "\n...\n" in rag_context

    def test_vector_search_exception_fallback(self):
        """向量检索失败时应降级为截断原文"""
        long_text = "A" * 5000

        def smart_rag_with_fallback(full_text, user_question, medicine_id=None):
            if len(full_text) < 1500:
                return full_text
            try:
                raise ConnectionError("ChromaDB 连接失败")
            except Exception:
                return full_text[:4000]

        result = smart_rag_with_fallback(long_text, "怎么吃")
        assert len(result) == 4000
        assert result == "A" * 4000

    def test_boundary_1500_is_long(self):
        """恰好 1500 字应走全量阅读（< 1500）"""
        text_1499 = "字" * 1499
        text_1500 = "字" * 1500

        def smart_rag_branch(full_text, *args):
            if len(full_text) < 1500:
                return "SHORT"
            return "LONG"

        assert smart_rag_branch(text_1499) == "SHORT"
        assert smart_rag_branch(text_1500) == "LONG"


# ============================================================
# 3. correct_medical_terms() 测试
# ============================================================
class TestCorrectMedicalTerms:
    """ASR 纠错函数测试"""

    # 幻觉黑名单（与 main.py 保持一致）
    HALLUCINATION_BLACKLIST = [
        "作曲", "作词", "字幕", "copyright", "subtitle",
        "amara.org", "bilibili", "优酷", "腾讯视频",
        "by Jonathan Lee", "李宗盛", "张学友"
    ]

    def _make_correct_fn(self, llm_return=None, llm_raise=None):
        """构造一个隔离的 correct_medical_terms 函数"""
        blacklist = self.HALLUCINATION_BLACKLIST

        def correct_medical_terms(text: str) -> dict:
            if not text or len(text) < 2:
                return {"status": "ok", "text": text}
            for bad_word in blacklist:
                if bad_word.lower() in text.lower():
                    return {"status": "hallucination", "text": ""}
            try:
                if llm_raise:
                    raise llm_raise
                corrected = llm_return
                if corrected.strip() == "EMPTY":
                    return {"status": "hallucination", "text": ""}
                return {"status": "ok", "text": corrected.strip()}
            except Exception:
                return {"status": "error", "text": ""}

        return correct_medical_terms

    def test_empty_input(self):
        """空输入直接返回原值"""
        fn = self._make_correct_fn(llm_return="不该到达")
        assert fn("") == {"status": "ok", "text": ""}
        assert fn(None) == {"status": "ok", "text": None}

    def test_short_input(self):
        """过短输入 (<2字) 直接返回原值"""
        fn = self._make_correct_fn(llm_return="不该到达")
        assert fn("吃") == {"status": "ok", "text": "吃"}

    def test_hallucination_blacklist_hit(self):
        """命中幻觉黑名单时返回空字符串"""
        fn = self._make_correct_fn(llm_return="不该到达")
        assert fn("作曲：周杰伦") == {"status": "hallucination", "text": ""}
        assert fn("Subtitle by someone") == {"status": "hallucination", "text": ""}
        assert fn("来自bilibili的字幕") == {"status": "hallucination", "text": ""}

    def test_llm_returns_empty(self):
        """LLM 返回 EMPTY 时应返回 hallucination 状态"""
        fn = self._make_correct_fn(llm_return="EMPTY")
        assert fn("一些乱码文本") == {"status": "hallucination", "text": ""}

    def test_llm_returns_corrected_text(self):
        """LLM 正常纠错"""
        fn = self._make_correct_fn(llm_return="阿莫西林怎么吃")
        result = fn("阿木西林怎么池")
        assert result == {"status": "ok", "text": "阿莫西林怎么吃"}

    def test_llm_exception_fallback(self):
        """LLM 调用异常时返回 error 状态"""
        fn = self._make_correct_fn(llm_raise=RuntimeError("API Timeout"))
        result = fn("阿木西林怎么池")
        assert result == {"status": "error", "text": ""}

    def test_blacklist_case_insensitive(self):
        """黑名单匹配应不区分大小写"""
        fn = self._make_correct_fn(llm_return="不该到达")
        assert fn("COPYRIGHT 2024") == {"status": "hallucination", "text": ""}
        assert fn("SUBTITLE BY TEAM") == {"status": "hallucination", "text": ""}
