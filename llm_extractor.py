"""LLM 智能字段提取层。

给一段 HTML / cleaned text 和一句话描述要什么字段，LLM 返回结构化 JSON。
比手写 CSS selector 更鲁棒（页面改版不会立即失败），代价是每次抽取要调 LLM。

设计原则：
- LLMClient 适配 openai / anthropic / deepseek，缺 key 时优雅 raise（不静默
  退到 noop，因为 LLM 抽取的目的就是用 LLM，不应该被静默跳过）
- LLMExtractor 接受任意 schema（自然语言描述或 JSON schema dict）
- 自动截断超长 HTML 到 ~15K 字符，避免 token 爆炸
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union


log = logging.getLogger(__name__)


LLMBackend = Literal["openai", "anthropic", "deepseek"]


class LLMNotAvailable(RuntimeError):
    """LLM 不可用：缺 key / 缺 SDK / 网络失败。"""


SYSTEM_PROMPT_EXTRACT = """你是一个网页数据提取助手。任务：从给定的 HTML 或纯文本中
提取用户指定的字段，输出严格 JSON。

输出要求：
1. 严格 JSON，键名与用户描述的字段对应
2. 找不到的字段值用 null，不要编造
3. 数字字段用数字类型（不是字符串），布尔字段用 true/false
4. 不要任何前后缀文字，只输出 JSON 对象

如果用户描述的是列表场景（如"所有商品的名称和价格"），返回
{"items": [...]} 形式。
"""


@dataclass(frozen=True)
class ExtractionResult:
    fields: Dict[str, Any]
    backend: str
    raw_llm_response: Optional[str] = None

    def to_dict(self) -> dict:
        return {"fields": self.fields, "backend": self.backend}


class LLMClient:
    """三 backend 统一接口。"""

    def __init__(
        self,
        backend: LLMBackend = "deepseek",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.backend = backend
        self.timeout = timeout
        self.api_key = api_key or self._default_key(backend)
        self.base_url = base_url or self._default_base_url(backend)
        self.model = model or self._default_model(backend)

    @staticmethod
    def _default_key(backend: LLMBackend) -> Optional[str]:
        return {
            "openai": os.getenv("OPENAI_API_KEY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY"),
            "deepseek": os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"),
        }.get(backend)

    @staticmethod
    def _default_base_url(backend: LLMBackend) -> Optional[str]:
        return {"deepseek": "https://api.deepseek.com/v1"}.get(backend)

    @staticmethod
    def _default_model(backend: LLMBackend) -> str:
        return {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku-20241022",
            "deepseek": "deepseek-chat",
        }.get(backend, "gpt-4o-mini")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def chat(self, system: str, user: str) -> str:
        if not self.is_available():
            raise LLMNotAvailable(
                f"{self.backend} backend 缺 API key（环境变量 "
                f"{self.backend.upper()}_API_KEY）"
            )
        if self.backend == "anthropic":
            return self._call_anthropic(system, user)
        return self._call_openai_compatible(system, user)

    def _call_openai_compatible(self, system: str, user: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise LLMNotAvailable("缺 openai SDK：pip install openai") from e
        client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,    # 提取任务用 0 温度
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or ""

    def _call_anthropic(self, system: str, user: str) -> str:
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise LLMNotAvailable("缺 anthropic SDK：pip install anthropic") from e
        client = Anthropic(api_key=self.api_key, timeout=self.timeout)
        resp = client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.0,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text if resp.content else ""


def _clean_html_for_llm(html: str, max_chars: int = 15000) -> str:
    """把 HTML 清洗成更适合喂 LLM 的精简文本。

    - 删除 <script>, <style>, <link>, <meta>, <noscript>, <svg> 标签内容
    - 保留 <a>/<img> 的关键属性
    - 折叠连续空白
    - 截断到 max_chars
    """
    text = re.sub(r"<(script|style|link|meta|noscript|svg)[^>]*>.*?</\1>",
                  "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # 简化 tag（保留语义关键的）
    text = re.sub(r"<(/?)(div|span|p|br|li|ul|ol|table|tr|td|th|h[1-6]|a|img)([^>]*)>",
                  r"<\1\2\3>", text, flags=re.IGNORECASE)
    # 折叠空白
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"
    return text.strip()


class LLMExtractor:
    """主入口：给 URL/HTML + 字段描述 → 结构化 JSON。"""

    def __init__(self, llm_client: Optional[LLMClient] = None,
                 backend: LLMBackend = "deepseek"):
        self.llm_client = llm_client or LLMClient(backend=backend)

    def extract_from_text(
        self,
        text: str,
        schema: Union[str, Dict],
        max_text_chars: int = 15000,
    ) -> ExtractionResult:
        """对已清洗的文本提取字段。

        Parameters
        ----------
        text : 已清洗的纯文本或 HTML 片段。
        schema : 字段描述。可以是：
            - str: 自然语言描述（如 "提取商品名称、价格、评分"）
            - dict: JSON schema 风格描述（如 {"name": "str", "price": "float"}）
        """
        if not self.llm_client.is_available():
            raise LLMNotAvailable("LLM client 没配 key，无法做智能提取")

        if isinstance(schema, dict):
            schema_text = "需要提取的字段：" + json.dumps(schema, ensure_ascii=False, indent=2)
        else:
            schema_text = f"需要提取的字段：{schema}"

        truncated = text[:max_text_chars]
        user_prompt = (
            f"{schema_text}\n\n"
            f"===== 网页内容（已清洗） =====\n{truncated}\n===== 内容结束 =====\n\n"
            f"按要求输出 JSON。"
        )

        raw = self.llm_client.chat(SYSTEM_PROMPT_EXTRACT, user_prompt)
        try:
            fields = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"LLM 返回的不是合法 JSON：{e}\n原始输出（前 500 字）：{raw[:500]}"
            ) from e

        return ExtractionResult(
            fields=fields,
            backend=self.llm_client.backend,
            raw_llm_response=raw,
        )

    def extract_from_html(
        self,
        html: str,
        schema: Union[str, Dict],
    ) -> ExtractionResult:
        """从原始 HTML 抽取：先清洗再丢给 LLM。"""
        cleaned = _clean_html_for_llm(html)
        return self.extract_from_text(cleaned, schema)

    def extract_from_url(
        self,
        url: str,
        schema: Union[str, Dict],
        timeout: int = 15,
    ) -> ExtractionResult:
        """从 URL 直接抽：fetch → clean → LLM。"""
        import requests
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return self.extract_from_html(resp.text, schema)
