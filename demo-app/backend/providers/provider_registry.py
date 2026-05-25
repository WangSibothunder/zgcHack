from __future__ import annotations

import os
from typing import Any

from .base import OCRResult
from .local_evidence_llm import LocalEvidenceLLMProvider
from .synthetic_ocr import SyntheticOCRProvider
from .vivo_bluelm_evidence import VivoBlueLMEvidenceProvider
from .vivo_general_ocr import VivoGeneralOCRProvider


def get_ocr_provider() -> tuple[str, str, bool]:
    """获取当前 OCR provider 状态。

    Returns:
        (provider_mode, provider_label, supports_bounding_boxes)
    """
    if not _external_enabled():
        ocr = SyntheticOCRProvider()
        result = ocr.recognize()
        return ocr.mode, ocr.label, result.supports_bounding_boxes

    provider_name = os.getenv("OCR_PROVIDER", "mock").lower()
    if provider_name == "vivo_general_ocr" or provider_name == "vivo":
        try:
            provider = VivoGeneralOCRProvider()
            result = provider.recognize()
            return provider.mode, provider.label, result.supports_bounding_boxes
        except Exception:
            syn = SyntheticOCRProvider()
            return syn.mode, syn.label + "（vivo 不可用回退）", True
    return "mock", "预置合成 OCR 回放", True


def get_llm_provider_info() -> tuple[str, str]:
    """获取当前 LLM provider 状态。

    Returns:
        (provider_mode, provider_label)
    """
    if not _external_enabled():
        llm = LocalEvidenceLLMProvider()
        return llm.mode, llm.label

    provider_name = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider_name in ("vivo_bluelm", "vivo", "bluelm"):
        return "vivo_chat_completions", "vivo Chat Completions 证据排序"
    return "mock", "本地证据检索"


def get_llm_provider() -> LocalEvidenceLLMProvider | VivoBlueLMEvidenceProvider:
    """获取 LLM provider 实例。"""
    if not _external_enabled():
        return LocalEvidenceLLMProvider()

    provider_name = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider_name in ("vivo_bluelm", "vivo", "bluelm"):
        return VivoBlueLMEvidenceProvider()
    return LocalEvidenceLLMProvider()


def get_provider_status() -> dict[str, Any]:
    """返回 provider 状态字典（用于 /api/v3/demo/providers/status）。"""
    ocr_mode, ocr_label, supports_bbox = get_ocr_provider()
    llm_mode, llm_label = get_llm_provider_info()
    external_enabled = _external_enabled()

    ocr_configured = external_enabled and os.getenv("VIVO_APP_ID", "") and os.getenv("VIVO_APP_KEY", "")
    llm_configured = external_enabled and os.getenv("VIVO_APP_ID", "") and os.getenv("VIVO_APP_KEY", "")

    return {
        "synthetic_only": True,
        "ocr": {
            "configured": bool(ocr_configured),
            "enabled": external_enabled and ocr_mode != "mock",
            "provider": ocr_mode,
            "label": ocr_label,
            "supports_bounding_boxes": supports_bbox,
            "last_smoke_test": "not_run",
        },
        "llm": {
            "configured": bool(llm_configured),
            "enabled": external_enabled and llm_mode != "mock",
            "provider": llm_mode,
            "label": llm_label,
            "last_smoke_test": "not_run",
        },
        "fallback_available": True,
        "notice": "仅对合成演示材料调用外部能力。",
    }


def _external_enabled() -> bool:
    return os.getenv("EXTERNAL_AI_ENABLED", "false").lower() == "true"
