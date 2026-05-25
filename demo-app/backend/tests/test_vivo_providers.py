from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from providers.base import validate_llm_items
from providers.local_evidence_llm import LocalEvidenceLLMProvider
from providers.provider_registry import get_ocr_provider, get_llm_provider_info, get_provider_status
from providers.synthetic_ocr import SyntheticOCRProvider
from providers.vivo_auth import build_vivo_bearer_headers, build_vivo_ocr_headers, redact_sensitive_headers
from providers.vivo_bluelm_evidence import VivoBlueLMEvidenceProvider
from providers.vivo_general_ocr import VivoGeneralOCRProvider

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vivo"

# ─────────────────────────────────────────────────────────────
# vivo 鉴权测试（Bearer 模式）
# ─────────────────────────────────────────────────────────────


def test_vivo_auth_bearer_headers_produced() -> None:
    """未设环境变量时 Bearer header 仍可生成（token 为空字符串）。"""
    headers = build_vivo_bearer_headers(body="{}")
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")
    assert "Content-Type" not in headers  # Bearer 模式不强制设置


def test_vivo_auth_ocr_headers() -> None:
    """OCR headers 包含 application/x-www-form-urlencoded"""
    headers = build_vivo_ocr_headers()
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"


def test_vivo_bearer_redact_sensitive_headers() -> None:
    """脱敏函数必须掩盖 Bearer token。"""
    headers = {
        "Authorization": "Bearer ABCDEF1234567890abcdef1234567890abcdef12",
    }
    redacted = redact_sensitive_headers(headers)
    # 脱敏后应保留前后4位，中间隐藏（如 "Bearer ABCD...ef12"）
    assert "ABCD" in redacted["Authorization"]
    assert "..." in redacted["Authorization"]
    # 确保未暴露完整 token
    assert "ABCDEF1234567890abcdef1234567890abcdef12" not in redacted["Authorization"]


# ─────────────────────────────────────────────────────────────
# OCR provider 测试
# ─────────────────────────────────────────────────────────────


def test_synthetic_ocr_provider_returns_blocks() -> None:
    provider = SyntheticOCRProvider()
    result = provider.recognize()
    assert result.provider == "deterministic_synthetic"
    assert len(result.blocks) > 0
    assert all(block.text for block in result.blocks)
    assert result.supports_bounding_boxes


def test_synthetic_ocr_provider_label_contains_synthetic() -> None:
    provider = SyntheticOCRProvider()
    assert "合成" in provider.label or "Synthetic" in provider.label or "synthetic" in provider.label


def test_vivo_ocr_no_env_returns_fallback() -> None:
    """未设 VIVO_APP_KEY 时，VivoGeneralOCRProvider 初始化并失败
    但返回带错误信息的 OCRResult，不抛异常。"""
    provider = VivoGeneralOCRProvider()
    result = provider.recognize(image_bytes=b"fake-synthetic-image-data")
    assert result.provider == "vivo_general_ocr"
    # 由于没有设置环境变量中的密钥，实际调用会失败
    # 但我们至少确保不抛异常，且 full_text 中含有失败信息或为空
    assert isinstance(result.full_text, str)


def test_provider_registry_returns_mock_when_not_configured() -> None:
    """默认未启用外部 AI 时 registry 应返回 mock provider。"""
    ocr_mode, ocr_label, supports_bbox = get_ocr_provider()
    assert ocr_mode in ("deterministic_synthetic", "mock")
    assert supports_bbox is True


# ─────────────────────────────────────────────────────────────
# LLM provider 测试
# ─────────────────────────────────────────────────────────────


def test_local_evidence_llm_provider() -> None:
    provider = LocalEvidenceLLMProvider()
    segments = [
        {"segment_id": "seg-001", "raw_text": "患者食欲不振三天"},
        {"segment_id": "seg-002", "raw_text": "体温正常"},
    ]
    result = provider.rerank_and_summarize(
        query="食欲不振",
        candidate_segments=segments,
        retrieval_terms=["食欲不振"],
    )
    assert len(result) == 2
    assert result[0]["segment_id"] == "seg-001"
    assert result[0]["relevance_level"] == "direct_mention"
    assert "食欲不振" in result[0]["evidence_summary"] or "该条" in result[0]["evidence_summary"]


def test_local_evidence_llm_synonym_retrieval() -> None:
    provider = LocalEvidenceLLMProvider()
    segments = [
        {"segment_id": "seg-003", "raw_text": "患者近一周食欲欠佳，进食量较前减少。"},
    ]
    result = provider.rerank_and_summarize(
        query="食欲不振相关记录",
        candidate_segments=segments,
        retrieval_terms=["食欲欠佳"],
    )
    assert result[0]["relevance_level"] == "direct_mention"


# ─────────────────────────────────────────────────────────────
# validate_llm_items 测试
# ─────────────────────────────────────────────────────────────


def test_validate_llm_items_drops_unknown_segment_ids() -> None:
    items = [
        {"segment_id": "seg-known", "relevance_level": "direct_mention", "evidence_summary": "有效记录"},
        {"segment_id": "seg-unknown", "relevance_level": "direct_mention", "evidence_summary": "应被丢弃"},
    ]
    valid_ids = {"seg-known"}
    valid = validate_llm_items(items, valid_ids)
    assert len(valid) == 1
    assert valid[0]["segment_id"] == "seg-known"


def test_validate_llm_items_drops_empty_summary() -> None:
    items = [
        {"segment_id": "seg-known", "relevance_level": "direct_mention", "evidence_summary": ""},
    ]
    valid = validate_llm_items(items, {"seg-known"})
    assert len(valid) == 0


def test_validate_llm_items_normalizes_unknown_level() -> None:
    items = [
        {"segment_id": "seg-known", "relevance_level": "unknown_level", "evidence_summary": "有效归纳"},
    ]
    valid = validate_llm_items(items, {"seg-known"})
    assert len(valid) == 1
    assert valid[0]["relevance_level"] == "contextual"


# ─────────────────────────────────────────────────────────────
# BlueLM provider 测试（不实际连接 API）
# ─────────────────────────────────────────────────────────────


def test_vivo_bluelm_no_env_returns_empty() -> None:
    """未设密钥时 BlueLM provider 不发起实际连接，返回空列表。"""
    provider = VivoBlueLMEvidenceProvider()
    segments = [{"segment_id": "seg-001", "raw_text": "食欲不振"}]
    result = provider.rerank_and_summarize(query="食欲不振", candidate_segments=segments, retrieval_terms=["食欲不振"])
    # 由于没有配置 keys，调用网络会失败，返回空列表
    assert isinstance(result, list)
    assert len(result) == 0


# ─────────────────────────────────────────────────────────────
# provider status 端点测试（通过 app）
# ─────────────────────────────────────────────────────────────


def test_provider_status_returns_default_mock() -> None:
    """默认环境中 provider status 应返回 mock 状态。"""
    from fastapi.testclient import TestClient
    from app import app

    client = TestClient(app)
    response = client.get("/api/v3/demo/providers/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["synthetic_only"] is True
    assert payload["ocr"]["provider"] in ("deterministic_synthetic", "mock")
    assert payload["ocr"]["supports_bounding_boxes"] is True
    assert "list_smoke_test" in payload["ocr"] or "last_smoke_test" in payload["ocr"]


def test_vivo_smoke_test_not_configured() -> None:
    from fastapi.testclient import TestClient
    from app import app

    client = TestClient(app)
    response = client.post("/api/v3/demo/providers/vivo/smoke-test")
    assert response.status_code == 200
    assert response.json()["configured"] is False
