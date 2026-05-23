"""llm_extractor.py 测试（不打真实 LLM）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_extractor import (
    ExtractionResult,
    LLMClient,
    LLMExtractor,
    LLMNotAvailable,
    _clean_html_for_llm,
)


# ---------------------------------------------------------------------------
# LLMClient
# ---------------------------------------------------------------------------


def test_llm_client_defaults():
    c = LLMClient()
    assert c.backend == "deepseek"
    assert c.model == "deepseek-chat"
    assert c.base_url == "https://api.deepseek.com/v1"


def test_llm_client_is_available_via_env(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert LLMClient().is_available() is False
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-x")
    assert LLMClient().is_available() is True


def test_llm_client_chat_raises_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LLMNotAvailable):
        LLMClient(backend="openai").chat("sys", "user")


# ---------------------------------------------------------------------------
# HTML 清洗
# ---------------------------------------------------------------------------


def test_clean_html_removes_scripts_and_styles():
    html = """
    <html>
      <head>
        <style>body { color: red; }</style>
        <script>console.log('hi');</script>
      </head>
      <body>
        <h1>Title</h1>
        <p>Para</p>
        <noscript>NoScript fallback</noscript>
      </body>
    </html>
    """
    cleaned = _clean_html_for_llm(html)
    assert "console.log" not in cleaned
    assert "color: red" not in cleaned
    assert "NoScript fallback" not in cleaned
    assert "Title" in cleaned
    assert "Para" in cleaned


def test_clean_html_removes_comments():
    html = "<p>Visible</p><!-- hidden comment -->"
    cleaned = _clean_html_for_llm(html)
    assert "hidden comment" not in cleaned
    assert "Visible" in cleaned


def test_clean_html_truncates_long_input():
    html = "<p>" + ("a" * 30_000) + "</p>"
    cleaned = _clean_html_for_llm(html, max_chars=1000)
    assert len(cleaned) < 2000
    assert "[truncated]" in cleaned


# ---------------------------------------------------------------------------
# LLMExtractor with mock LLM
# ---------------------------------------------------------------------------


def test_extract_from_text_calls_llm_and_parses_json():
    fake_client = MagicMock(spec=LLMClient)
    fake_client.is_available.return_value = True
    fake_client.backend = "deepseek"
    fake_client.chat.return_value = json.dumps({
        "name": "iPhone 15 Pro",
        "price": 7999,
        "in_stock": True,
        "rating": 4.7,
    })

    extractor = LLMExtractor(llm_client=fake_client)
    result = extractor.extract_from_text(
        "<p>iPhone 15 Pro ￥7999 现货 4.7 分</p>",
        schema="提取商品名、价格、库存、评分",
    )
    assert isinstance(result, ExtractionResult)
    assert result.fields["name"] == "iPhone 15 Pro"
    assert result.fields["price"] == 7999
    assert result.fields["in_stock"] is True
    assert result.fields["rating"] == 4.7
    assert result.backend == "deepseek"


def test_extract_supports_dict_schema():
    fake_client = MagicMock(spec=LLMClient)
    fake_client.is_available.return_value = True
    fake_client.backend = "openai"
    fake_client.chat.return_value = json.dumps({"title": "x", "author": "y"})

    schema = {"title": "str", "author": "str"}
    result = LLMExtractor(llm_client=fake_client).extract_from_text("html", schema)
    assert result.fields["title"] == "x"


def test_extract_raises_when_llm_unavailable(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMNotAvailable):
        LLMExtractor().extract_from_text("html", "x")


def test_extract_raises_on_invalid_json():
    fake_client = MagicMock(spec=LLMClient)
    fake_client.is_available.return_value = True
    fake_client.backend = "deepseek"
    fake_client.chat.return_value = "Sorry I cannot output JSON"

    with pytest.raises(ValueError, match="JSON"):
        LLMExtractor(llm_client=fake_client).extract_from_text("html", "x")


def test_extract_from_html_strips_scripts():
    """extract_from_html 应当先调 _clean_html_for_llm。"""
    fake_client = MagicMock(spec=LLMClient)
    fake_client.is_available.return_value = True
    fake_client.backend = "deepseek"
    fake_client.chat.return_value = json.dumps({"x": 1})

    html = "<script>secret_token</script><p>visible</p>"
    extractor = LLMExtractor(llm_client=fake_client)
    extractor.extract_from_html(html, "提取 x")

    # 检查传给 LLM 的 user prompt 不含 script 内容
    call_args = fake_client.chat.call_args
    user_prompt = call_args[0][1] if call_args[0] else call_args.kwargs.get("user", "")
    assert "secret_token" not in user_prompt
    assert "visible" in user_prompt


def test_extraction_result_to_dict():
    r = ExtractionResult(fields={"a": 1}, backend="openai", raw_llm_response="...")
    d = r.to_dict()
    assert d == {"fields": {"a": 1}, "backend": "openai"}
    # raw_llm_response 不应出现在 to_dict
    assert "raw_llm_response" not in d
