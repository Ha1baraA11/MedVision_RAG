from services.chat_model import DEFAULT_CHAT_MODEL, resolve_chat_model_name


def test_resolve_chat_model_name_accepts_pro():
    assert resolve_chat_model_name("deepseek-v4-pro") == "deepseek-v4-pro"


def test_resolve_chat_model_name_accepts_flash():
    assert resolve_chat_model_name("deepseek-v4-flash") == "deepseek-v4-flash"


def test_resolve_chat_model_name_falls_back_for_empty():
    assert resolve_chat_model_name(None) == DEFAULT_CHAT_MODEL
    assert resolve_chat_model_name("") == DEFAULT_CHAT_MODEL


def test_resolve_chat_model_name_falls_back_for_invalid_value():
    assert resolve_chat_model_name("deepseek-v3") == DEFAULT_CHAT_MODEL
