from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from .base import validate_llm_items
from .vivo_auth import build_vivo_sign_headers, redact_sensitive_headers

VIVO_LLM_HOST = "api-ai.vivo.com.cn"
VIVO_LLM_PATH = "/v1/chat/completions"
VIVO_LLM_MODEL = "BlueLM"
DEFAULT_TIMEOUT = 45

# 系统提示词模板路径
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "vivo_evidence_linked_search_system.txt"


class VivoBlueLMEvidenceProvider:
    """vivo BlueLM evidence LLM provider。

    连接 vivo BlueLM API，对已召回的候选 DocumentSegment 进行相关性排序
    与材料归纳。遵循 grounded 链路：
    1. 仅接收 query + candidate segments；
    2. 输出必须绑定 segment_id；
    3. 校验输出，失败时回退。

    注意：在从官方文档确认 BlueLM 的 host/path/model 字段之前，
    本 adapter 使用当前可推测的通用 OpenAI-compatible 接口模式。
    如果官方文档与此不同，必须更新。
    """

    mode = "vivo_bluelm"
    label = "vivo BlueLM 证据排序"

    def __init__(self) -> None:
        self._host = os.getenv("VIVO_LLM_HOST", VIVO_LLM_HOST)
        self._path = os.getenv("VIVO_LLM_PATH", VIVO_LLM_PATH)
        self._model = os.getenv("VIVO_LLM_MODEL", VIVO_LLM_MODEL)
        self._timeout = int(os.getenv("VIVO_LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT)))
        self._stream = os.getenv("VIVO_LLM_STREAM", "false").lower() == "true"

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

        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": self._stream,
            "temperature": 0.1,
            "max_tokens": 2048,
        }

        body_str = json.dumps(body, ensure_ascii=False)
        headers = build_vivo_sign_headers(body=body_str)
        url = f"https://{self._host}{self._path}"

        try:
            resp = httpx.post(url, headers=headers, content=body_str, timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        # 解析响应（支持 OpenAI-compatible 结构）
        content = self._extract_content(data)
        if not content:
            return []

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            return []

        items = result.get("items", [])
        if not isinstance(items, list):
            return []

        valid_ids = {seg["segment_id"] for seg in candidate_segments}
        return validate_llm_items(items, valid_ids)

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
        return f"医生问题：{query}\n\n候选片段：\n{segments_str}"

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
