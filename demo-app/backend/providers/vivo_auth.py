from __future__ import annotations

import os
from typing import Any


def build_vivo_bearer_headers(body: str = "") -> dict[str, str]:
    """构建 vivo AI 平台 API 鉴权 header。

    根据 v0.9.1 已核实 PRD，两个 API（OCR、Chat Completions）
    均使用 Authorization: Bearer <AppKey> 鉴权模式。

    Args:
        body: 请求体字符串（仅用于接口兼容，Bearer 模式不参与签名）。

    Returns:
        包含鉴权 headers 的字典。
    """
    _ = body  # Bearer 模式 body 不参与签名
    app_key = os.getenv("VIVO_APP_KEY", "")
    return {
        "Authorization": f"Bearer {app_key}",
    }


def build_vivo_ocr_headers() -> dict[str, str]:
    """构建 vivo 通用 OCR API 请求 header。

    OCR endpoint 使用 application/x-www-form-urlencoded + Bearer token。
    """
    app_key = os.getenv("VIVO_APP_KEY", "")
    return {
        "Authorization": f"Bearer {app_key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def redact_sensitive_headers(headers: dict[str, str]) -> dict[str, str]:
    """脱敏 headers 中可能含密钥的字段，用于日志。"""
    result = dict(headers)
    auth = result.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        if len(token) > 8:
            result["Authorization"] = f"Bearer {token[:4]}...{token[-4:]}"
        elif token:
            result["Authorization"] = "Bearer ***"
    return result
