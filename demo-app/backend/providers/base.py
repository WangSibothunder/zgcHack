from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


class OCRBlock(BaseModel):
    block_id: str
    text: str
    bbox: list[float] | None = None  # [x_min, y_min, x_max, y_max]
    polygon: list[list[float]] | None = None  # 若原响应返回四点坐标，可同时保留
    coordinate_mode: str | None = None  # "relative" / "absolute"
    confidence: float | None = None


class OCRResult(BaseModel):
    provider: Literal["vivo_general_ocr", "deterministic_synthetic", "mock"] = "mock"
    provider_label: str = "预置合成 OCR 回放"
    full_text: str = ""
    blocks: list[OCRBlock] = Field(default_factory=list)
    angle: int | None = None
    supports_bounding_boxes: bool = False
    synthetic: bool = True
    raw_response_persisted: bool = False
    warning_messages: list[str] = Field(default_factory=list)


class LLMGroundedItem(BaseModel):
    segment_id: str
    relevance_level: Literal["direct_mention", "synonymous_mention", "contextual"] = "contextual"
    evidence_summary: str = ""


class LLMGroundedResult(BaseModel):
    expanded_terms: list[str] = Field(default_factory=list)
    items: list[LLMGroundedItem] = Field(default_factory=list)


class EvidenceLLMProvider(Protocol):
    """协议：证据联查 LLM Provider

    所有 provider 必须实现此协议。LLM 的唯一任务：
    1. 识别检索主题与同义表述。
    2. 在已召回候选片段中判断相关性。
    3. 对每条证据生成不超过原文的短归纳。
    4. 返回引用的 segment_id。
    """

    mode: str
    label: str

    def rerank_and_summarize(
        self,
        query: str,
        candidate_segments: list[dict[str, Any]],
        retrieval_terms: list[str],
    ) -> list[dict[str, str]]:
        ...


class OCRProviderProtocol(Protocol):
    """协议：OCR Provider

    所有 OCR provider 必须实现此协议。
    """

    mode: str
    label: str

    def recognize(self, image_path: str | None = None, image_bytes: bytes | None = None) -> OCRResult:
        ...


def validate_llm_items(
    items: list[dict[str, str]],
    candidate_segment_ids: set[str],
) -> list[dict[str, str]]:
    """校验 LLM 返回结果：丢弃无效 segment_id 与字段不完整的 item。"""
    valid: list[dict[str, str]] = []
    allowed_levels = {"direct_mention", "synonymous_mention", "contextual"}
    for item in items:
        segment_id = item.get("segment_id", "")
        if segment_id not in candidate_segment_ids:
            continue
        level = item.get("relevance_level", "contextual")
        if level not in allowed_levels:
            item["relevance_level"] = "contextual"
        summary = item.get("evidence_summary", "").strip()
        if not summary or len(summary) > 100:
            continue
        valid.append(item)
    return valid
