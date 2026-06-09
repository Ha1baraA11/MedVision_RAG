import importlib
import sys
import types
from pathlib import Path

import pytest


BACKEND_AI_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_AI_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_AI_DIR))


class _DummyChain:
    def __or__(self, other):
        return self

    def invoke(self, payload):
        return "测试药品"


class _FakePromptTemplate:
    @staticmethod
    def from_messages(messages):
        return _DummyChain()


class _FakeStrOutputParser:
    def __init__(self, *args, **kwargs):
        pass


@pytest.fixture
def ocr_module(monkeypatch, tmp_path):
    fake_logger = types.SimpleNamespace(
        info=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
    )
    fake_ocr_engine = types.SimpleNamespace(OCR=lambda path: None)

    monkeypatch.setitem(sys.modules, "ocrmac", types.SimpleNamespace(ocrmac=fake_ocr_engine))
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        types.SimpleNamespace(image_to_string=lambda image, lang=None: ""),
    )
    monkeypatch.setitem(
        sys.modules,
        "langchain_core.prompts",
        types.SimpleNamespace(ChatPromptTemplate=_FakePromptTemplate),
    )
    monkeypatch.setitem(
        sys.modules,
        "langchain_core.output_parsers",
        types.SimpleNamespace(StrOutputParser=_FakeStrOutputParser),
    )
    monkeypatch.setitem(
        sys.modules,
        "core.logging_config",
        types.SimpleNamespace(logger=fake_logger, TraceMiddleware=object),
    )
    monkeypatch.setitem(
        sys.modules,
        "core.config",
        types.SimpleNamespace(llm=object(), TEMP_DIR=str(tmp_path)),
    )

    sys.modules.pop("services.ocr", None)
    module = importlib.import_module("services.ocr")
    yield module
    sys.modules.pop("services.ocr", None)


class _FakeRect:
    def __init__(self, width, height):
        self.width = width
        self.height = height


class _FakePagePixmap:
    def __init__(self, output_text):
        self.output_text = output_text

    def save(self, path):
        Path(path).write_bytes(self.output_text.encode("utf-8"))


class _FakeRenderedPage:
    def __init__(self, text="", images=None):
        self._text = text
        self._images = images or []
        self.rect = _FakeRect(600, 800)
        self.render_calls = 0

    def get_text(self, mode="text"):
        return self._text

    def get_images(self, full=True):
        return self._images

    def get_image_rects(self, xref):
        return [_FakeRect(540, 760)]

    def get_pixmap(self, matrix=None, colorspace=None, alpha=False):
        self.render_calls += 1
        return _FakePagePixmap("rendered-page")


class _FakeDoc:
    def __init__(self, pages):
        self._pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __iter__(self):
        return iter(self._pages)


class _FakeImagePixmap:
    def __init__(self, doc, xref):
        self.alpha = False
        self.n = 3
        self.doc = doc
        self.xref = xref

    def save(self, path):
        Path(path).write_bytes(f"image-{self.xref}".encode("utf-8"))


def test_extract_text_from_pdf_prefers_embedded_image_ocr(monkeypatch, ocr_module):
    page = _FakeRenderedPage(text="", images=[(11, 0, 2000, 1400, 8, "DeviceRGB", "", "img1", "DCTDecode")])
    fake_fitz = types.SimpleNamespace(
        open=lambda path: _FakeDoc([page]),
        Pixmap=_FakeImagePixmap,
        Matrix=lambda x, y: (x, y),
        csRGB="rgb",
        csGRAY="gray",
    )
    monkeypatch.setitem(sys.modules, "fitz", fake_fitz)
    monkeypatch.setattr(ocr_module, "run_ocr", lambda path, min_text_length=1: "图像 OCR 命中")

    text = ocr_module.extract_text_from_pdf("/tmp/dummy.pdf")

    assert "图像 OCR 命中" in text
    assert page.render_calls == 0


def test_extract_text_from_pdf_renders_only_when_needed(monkeypatch, ocr_module):
    page = _FakeRenderedPage(text="", images=[])
    fake_fitz = types.SimpleNamespace(
        open=lambda path: _FakeDoc([page]),
        Pixmap=_FakeImagePixmap,
        Matrix=lambda x, y: (x, y),
        csRGB="rgb",
        csGRAY="gray",
    )
    monkeypatch.setitem(sys.modules, "fitz", fake_fitz)
    monkeypatch.setattr(ocr_module, "run_ocr", lambda path, min_text_length=1: "渲染 OCR 命中")

    text = ocr_module.extract_text_from_pdf("/tmp/dummy.pdf")

    assert "渲染 OCR 命中" in text
    assert page.render_calls == 1
