from __future__ import annotations

import os
from typing import Protocol


class SyntheticExternalApiError(ValueError):
    pass


class ExternalOCRApiProvider:
    mode = "external_ocr_api_placeholder"

    def map_response(self, payload: dict[str, object]) -> dict[str, object]:
        blocks: list[dict[str, object]] = []
        raw_blocks = payload.get("blocks") if isinstance(payload.get("blocks"), list) else []
        for index, item in enumerate(raw_blocks, start=1):
            if not isinstance(item, dict):
                continue
            bbox = item.get("bbox")
            blocks.append(
                {
                    "block_id": str(item.get("block_id") or f"external-ocr-{index:03d}"),
                    "text": str(item.get("text") or ""),
                    "bbox": bbox if _is_bbox(bbox) else None,
                    "confidence": item.get("confidence"),
                }
            )
        full_text = str(payload.get("full_text") or "\n".join(str(block["text"]) for block in blocks))
        return {
            "provider_mode": self.mode,
            "full_text": full_text,
            "blocks": blocks,
            "supports_bounding_boxes": any(block.get("bbox") for block in blocks),
        }


def _is_bbox(value: object) -> bool:
    return isinstance(value, list) and len(value) == 4 and all(isinstance(item, (int, float)) for item in value)


def assert_synthetic_external_api_allowed(payload: dict[str, object]) -> None:
    if payload.get("synthetic") is not True:
        raise SyntheticExternalApiError("外部 API 仅允许处理 synthetic=true 的合成演示数据。")
    if os.getenv("ALLOW_EXTERNAL_API_FOR_SYNTHETIC_ONLY", "true").lower() != "true":
        raise SyntheticExternalApiError("当前环境未允许 synthetic-only 外部 API 调用。")


class EvidenceLLMProvider(Protocol):
    mode: str

    def rerank_and_summarize(
        self,
        query: str,
        candidate_segments: list[dict[str, object]],
        retrieval_terms: list[str],
    ) -> list[dict[str, str]]:
        ...


class MockEvidenceLLMProvider:
    mode = "mock"

    def rerank_and_summarize(
        self,
        query: str,
        candidate_segments: list[dict[str, object]],
        retrieval_terms: list[str],
    ) -> list[dict[str, str]]:
        del query
        results: list[dict[str, str]] = []
        for segment in candidate_segments:
            raw_text = str(segment.get("raw_text", ""))
            matched = [term for term in retrieval_terms if term and term.lower() in raw_text.lower()]
            relevance_level = "direct_mention" if matched[:1] and matched[0] in raw_text else "synonymous_mention"
            if not matched:
                relevance_level = "contextual"
            results.append(
                {
                    "segment_id": str(segment["segment_id"]),
                    "relevance_level": relevance_level,
                    "evidence_summary": summarize_from_source(raw_text, matched[:1]),
                }
            )
        return results


class ExternalEvidenceLLMProvider:
    mode = "unavailable_fallback"

    def rerank_and_summarize(
        self,
        query: str,
        candidate_segments: list[dict[str, object]],
        retrieval_terms: list[str],
    ) -> list[dict[str, str]]:
        del query, retrieval_terms
        assert_synthetic_external_api_allowed({"synthetic": all(item.get("synthetic") is True for item in candidate_segments)})
        return []


def get_llm_provider() -> EvidenceLLMProvider:
    external_enabled = os.getenv("EXTERNAL_AI_ENABLED", "false").lower() == "true"
    provider_name = os.getenv("LLM_PROVIDER", "mock").lower()
    if external_enabled and provider_name != "mock":
        return ExternalEvidenceLLMProvider()
    return MockEvidenceLLMProvider()


def summarize_from_source(raw_text: str, matched_terms: list[str]) -> str:
    term = matched_terms[0] if matched_terms else "相关表述"
    compact = raw_text.strip("。")
    if term and term in raw_text:
        return f"该条原文记载包含“{term}”相关表述。"
    return f"该条记录与检索主题相关，原文为“{compact[:42]}”。"
