from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import httpx

from .base import validate_llm_items
from .vivo_auth import redact_sensitive_headers

VIVO_LLM_DEFAULT_BASE_URL = "https://api-ai.vivo.com.cn/v1"
VIVO_LLM_DEFAULT_PATH = "/chat/completions"
VIVO_LLM_DEFAULT_MODEL = "qwen3.5-plus"
DEFAULT_TIMEOUT = 45

# 系统提示词模板路径
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "vivo_evidence_linked_search_system.txt"


class VivoBlueLMEvidenceProvider:
    """vivo BlueLM / Chat Completions evidence LLM provider。

    根据已核实 PRD v0.9.1-Resolved 文档接入 vivo 大模型 API。

    请求特征：
    - Content-Type: application/json
    - Authorization: Bearer AppKey
    - Query 参数: request_id (默认，兼容重试 requestId)
    - OpenAI-compatible Chat Completions 格式
    - 不使用 Function Calling

    注意事项：
    - 仅对本地召回的候选 DocumentSegment 进行相关性排序与材料归纳
    - 输出结果必须绑定有效的 segment_id
    - 解析失败、限流、审核干预、无权限时回退本地检索
    """

    mode = "vivo_chat_completions"
    label = "vivo Chat Completions 证据排序"

    def __init__(self) -> None:
        base_url = os.getenv("VIVO_LLM_BASE_URL", VIVO_LLM_DEFAULT_BASE_URL)
        path = os.getenv("VIVO_LLM_PATH", VIVO_LLM_DEFAULT_PATH)
        self._url = f"{base_url.rstrip('/')}{path}"
        self._model = os.getenv("VIVO_LLM_MODEL", VIVO_LLM_DEFAULT_MODEL)
        self._timeout = int(os.getenv("VIVO_LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT)))
        self._temperature = float(os.getenv("VIVO_LLM_TEMPERATURE", "0.1"))
        self._max_tokens = int(os.getenv("VIVO_LLM_MAX_TOKENS", "1024"))
        self._reasoning_effort = os.getenv("VIVO_LLM_REASONING_EFFORT", "minimal")
        self._enable_thinking = os.getenv("VIVO_LLM_ENABLE_THINKING", "false").lower() == "true"
        self._request_id_style = os.getenv("VIVO_LLM_REQUEST_ID_QUERY_STYLE", "request_id")
        self._app_key = os.getenv("VIVO_APP_KEY", "")
        self._retried_request_id = False

    def rerank_and_summarize(
        self,
        query: str,
        candidate_segments: list[dict[str, Any]],
        retrieval_terms: list[str],
    ) -> list[dict[str, str]]:
        from services.external_ai import assert_synthetic_external_api_allowed

        assert_synthetic_external_api_allowed({"synthetic": True})

        if not query or not candidate_segments:
            return []

        system_prompt = self._load_system_prompt()
        user_prompt = self._build_user_prompt(query, candidate_segments)

        body = self._build_request_body(system_prompt, user_prompt)
        _, content = self._send_request(body)

        if content is None:
            # 若首次 request_id 参数异常，兼容重试
            if not self._retried_request_id:
                self._retried_request_id = True
                current_style = self._request_id_style
                alt_style = "requestId" if current_style == "request_id" else "request_id"
                # 只做一次重试
                _, content = self._send_request(body, query_style_override=alt_style)

        if content is None:
            return []

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return []

        items = parsed.get("items", [])
        if not isinstance(items, list):
            return []

        valid_ids = {seg["segment_id"] for seg in candidate_segments}
        return validate_llm_items(items, valid_ids)

    def _build_request_body(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }

        # 根据模型添加特定字段
        model_lower = self._model.lower()
        if "deepseek" in model_lower:
            body["reasoning_effort"] = self._reasoning_effort
        elif "doubao" in model_lower:
            pass  # Doubao 系列默认配置即可
        elif "qwen" in model_lower:
            if not self._enable_thinking:
                body["enable_thinking"] = False

        return body

    def _send_request(
        self,
        body: dict[str, Any],
        query_style_override: str | None = None,
    ) -> tuple[int, str | None]:
        """发送 LLM 请求。

        Returns:
            (HTTP status code, content text or None on failure)
        """
        import base64 as _b64

        body_str = json.dumps(body, ensure_ascii=False)

        headers = {
            "Authorization": f"Bearer {self._app_key}",
            "Content-Type": "application/json",
        }
        params: dict[str, str] = {}
        style = query_style_override or self._request_id_style
        params[style] = str(uuid.uuid4())

        try:
            resp = httpx.post(
                self._url,
                headers=headers,
                params=params,
                content=body_str,
                timeout=self._timeout,
            )

            if resp.status_code == 400:
                # 检查是否 request id 参数名问题
                try:
                    err_data = resp.json()
                    if err_data.get("error_code") == 1001:
                        return 400, None
                except Exception:
                    pass
                return resp.status_code, None

            if resp.status_code == 403 or resp.status_code == 401:
                return resp.status_code, None

            if resp.status_code == 429:
                return resp.status_code, None

            resp.raise_for_status()
            data = resp.json()

            # 检查错误码
            error_code = data.get("error_code", 0)
            if error_code == 1007:
                return 200, None  # 审核干预，回退
            if error_code == 30001 or error_code == 2003:
                return 200, None  # 限流/用量限制

            content = self._extract_content(data)
            return resp.status_code, content

        except httpx.TimeoutException:
            return 0, None
        except Exception:
            return 0, None

    def _load_system_prompt(self) -> str:
        if PROMPT_PATH.exists():
            return PROMPT_PATH.read_text(encoding="utf-8")
        # fallback prompt
        return (
            "你是'转诊迹'中的证据联查排序模块，仅处理合成演示病历文本。\n"
            "从给定 candidate_segments 中筛选与医生查询直接相关的片段，按相关性排序，"
            "为每条生成严格基于原文的短归纳。\n"
            "1. 只能依据候选片段，不得添加外部医学知识。\n"
            "2. 不得输出诊断、治疗建议、病因推断。\n"
            "3. 每条结果必须返回存在的 segment_id。\n"
            "4. items 为空表示无相关证据。\n"
            "返回 JSON: {\"items\": [{\"segment_id\": \"...\", "
            "\"relevance_level\": \"direct_mention|synonymous_mention|contextual\", "
            "\"evidence_summary\": \"...\"}]}"
        )

    def _build_user_prompt(
        self, query: str, candidate_segments: list[dict[str, Any]]
    ) -> str:
        segments_str = json.dumps(
            [
                {
                    "segment_id": seg["segment_id"],
                    "date": seg.get("document_date"),
                    "document_type": seg.get("document_type"),
                    "raw_text": seg.get("raw_text", ""),
                }
                for seg in candidate_segments
            ],
            ensure_ascii=False,
            indent=2,
        )
        return json.dumps({
            "query": query,
            "candidate_segments": json.loads(segments_str),
        }, ensure_ascii=False)

    def _extract_content(self, data: dict[str, Any]) -> str | None:
        """从 LLM 响应中提取文本内容。"""
        # OpenAI-compatible
        choices = data.get("choices")
        if isinstance(choices, list) and len(choices) > 0:
            choice = choices[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            if content:
                return content
            delta = choice.get("delta", {})
            content = delta.get("content", "")
            if content:
                return content
        # vivo 自有结构
        result = data.get("result") or data.get("data") or {}
        if isinstance(result, dict):
            content = result.get("content") or result.get("text") or result.get("response") or ""
            if content:
                return str(content)
        return None
