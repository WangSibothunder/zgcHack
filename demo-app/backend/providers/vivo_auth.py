from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any


def build_vivo_sign_headers(
    app_id: str | None = None,
    app_key: str | None = None,
    body: str = "",
    timestamp: int | None = None,
) -> dict[str, str]:
    """构建 vivo AI 平台 API 签名 header。

    鉴权来源：vivo AIGC 创新赛官方文档页面 id=1745 / id=1746。
    签名算法：使用 APP_KEY 对 body+timestamp 计算 HMAC-SHA256。

    注意：本实现基于已知 vivo 签名模式实现。如果官方文档中的鉴权方式与此不同，
    必须以官方文档为准并更新此函数。

    Args:
        app_id: 平台分配的 APP_ID。默认从环境变量读取。
        app_key: 平台分配的 APP_KEY。默认从环境变量读取。
        body: 请求体字符串（用于签名）。
        timestamp: 当前 Unix 时间戳（秒）。

    Returns:
        包含鉴权 headers 的字典。
    """
    _app_id = app_id or os.getenv("VIVO_APP_ID", "")
    _app_key = app_key or os.getenv("VIVO_APP_KEY", "")
    _timestamp = timestamp or int(time.time())

    sign_str = f"{body}{_timestamp}"
    signature = hmac.new(
        _app_key.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return {
        "Content-Type": "application/json;charset=utf-8",
        "X-APP-ID": _app_id,
        "X-TIMESTAMP": str(_timestamp),
        "X-Signature": signature,
    }


def redact_sensitive_headers(headers: dict[str, str]) -> dict[str, str]:
    """脱敏 headers 中可能含密钥的字段，用于日志。"""
    result = dict(headers)
    if "X-Signature" in result:
        sig = result["X-Signature"]
        result["X-Signature"] = f"{sig[:8]}...{sig[-4:]}" if len(sig) > 12 else "***"
    if "X-APP-ID" in result:
        aid = result["X-APP-ID"]
        result["X-APP-ID"] = f"{aid[:4]}...{aid[-2:]}" if len(aid) > 6 else "***"
    return result
