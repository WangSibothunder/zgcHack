from __future__ import annotations

import base64
import os
import uuid
from typing import Any

import httpx

from services.external_ai import assert_synthetic_external_api_allowed
from .base import OCRBlock, OCRResult
from .vivo_auth import build_vivo_ocr_headers, redact_sensitive_headers

VIVO_OCR_DEFAULT_BASE_URL = "http://api-ai.vivo.com.cn"
VIVO_OCR_DEFAULT_PATH = "/ocr/general_recognition"
DEFAULT_TIMEOUT = 10


class VivoGeneralOCRProvider:
    """vivo 通用 OCR provider。

    根据已核实 PRD v0.9.1-Resolved 文档接入 vivo AI 平台通用 OCR API。

    请求特征：
    - Content-Type: application/x-www-form-urlencoded
    - Authorization: Bearer AppKey
    - Query: requestId=<uuid>
    - Form body: image (base64), pos=2, businessid, sessid

    位置返回：pos=2 返回相对坐标 (top_left/top_right/down_left/down_right)，
    转换为 polygon 与 bbox。
    置信度：官方文档未提供该字段，live OCR 结果 confidence=null。

    重要安全限制：
    - 官方文档给出 HTTP endpoint，优先测试 HTTPS 可用性
    - 仅允许处理 synthetic=true 的数据
    """

    mode = "vivo_general_ocr"
    label = "vivo 通用 OCR"

    def __init__(self) -> None:
        base_url = os.getenv("VIVO_OCR_BASE_URL", VIVO_OCR_DEFAULT_BASE_URL)
        path = os.getenv("VIVO_OCR_PATH", VIVO_OCR_DEFAULT_PATH)
        self._url = f"{base_url.rstrip('/')}{path}"
        self._timeout = int(os.getenv("VIVO_OCR_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT)))
        self._position_mode = os.getenv("VIVO_OCR_POS", "2")
        self._business_id_override = os.getenv("VIVO_OCR_BUSINESS_ID_OVERRIDE", "")
        self._app_id = os.getenv("VIVO_APP_ID", "")
        self._app_key = os.getenv("VIVO_APP_KEY", "")

    def recognize(self, image_path: str | None = None, image_bytes: bytes | None = None) -> OCRResult:
        assert_synthetic_external_api_allowed({"synthetic": True})

        if image_bytes is None and image_path:
            with open(image_path, "rb") as fp:
                image_bytes = fp.read()

        if image_bytes is None:
            return OCRResult(
                provider="vivo_general_ocr",
                provider_label=self.label,
                full_text="",
                blocks=[],
                supports_bounding_boxes=False,
                synthetic=True,
                raw_response_persisted=False,
            )

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        request_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        business_id = (
            self._business_id_override
            or f"aigc{self._app_id}"
        )

        headers = build_vivo_ocr_headers()
        params = {"requestId": request_id}
        data = {
            "image": image_base64,
            "pos": self._position_mode,
            "businessid": business_id,
            "sessid": session_id,
        }

        try:
            resp = httpx.post(
                self._url,
                headers=headers,
                params=params,
                data=data,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data_resp: dict[str, Any] = resp.json()
        except Exception as exc:
            return OCRResult(
                provider="vivo_general_ocr",
                provider_label=self.label,
                full_text=f"vivo OCR 调用失败：{exc}",
                blocks=[],
                supports_bounding_boxes=False,
                synthetic=True,
                raw_response_persisted=False,
            )

        # 解析响应：支持 pos=2 结构（result.OCR）
        blocks: list[OCRBlock] = []
        angle: int | None = None
        warnings: list[str] = []

        # 检查 error_code
        error_code = data_resp.get("error_code", 0)
        if error_code != 0:
            return OCRResult(
                provider="vivo_general_ocr",
                provider_label=self.label,
                full_text=f"vivo OCR 返回错误：error_code={error_code}",
                blocks=[],
                supports_bounding_boxes=False,
                synthetic=True,
                raw_response_persisted=False,
            )

        result = data_resp.get("result", {})
        if isinstance(result, dict):
            angle = result.get("angle")
            ocr_entries = result.get("OCR", [])
            if not isinstance(ocr_entries, list):
                ocr_entries = []

            for entry in ocr_entries:
                if not isinstance(entry, dict):
                    continue
                words = entry.get("words", "")
                location = entry.get("location")
                if not words or not location:
                    continue

                # 从四点坐标构建 polygon
                polygon: list[list[float]] | None = None
                bbox: list[float] | None = None

                try:
                    top_left = location.get("top_left", {})
                    top_right = location.get("top_right", {})
                    down_left = location.get("down_left", {})
                    down_right = location.get("down_right", {})

                    polygon = [
                        [float(top_left.get("x", 0)), float(top_left.get("y", 0))],
                        [float(top_right.get("x", 0)), float(top_right.get("y", 0))],
                        [float(down_right.get("x", 0)), float(down_right.get("y", 0))],
                        [float(down_left.get("x", 0)), float(down_left.get("y", 0))],
                    ]

                    xs = [pt[0] for pt in polygon]
                    ys = [pt[1] for pt in polygon]
                    bbox = [min(xs), min(ys), max(xs), max(ys)]
                except (ValueError, TypeError, AttributeError):
                    pass

                blocks.append(OCRBlock(
                    block_id=f"vivo-ocr-{len(blocks):04d}",
                    text=words,
                    bbox=bbox,
                    polygon=polygon,
                    coordinate_mode="relative" if bbox else None,
                    confidence=None,  # 官方文档未提供置信度字段
                ))

        # 回退：无 result.OCR 时尝试直接读 full_text
        full_text = ""
        if blocks:
            full_text = " ".join(b.text for b in blocks)
        else:
            full_text = data_resp.get("full_text") or data_resp.get("text", "")

        supports_bbox = any(b.bbox is not None for b in blocks)

        if not supports_bbox and blocks:
            warnings.append("vivo OCR pos=2 响应未返回可解析坐标，无法提供原图高亮。")

        return OCRResult(
            provider="vivo_general_ocr",
            provider_label=self.label,
            full_text=full_text,
            blocks=blocks,
            angle=angle,
            supports_bounding_boxes=supports_bbox,
            synthetic=True,
            raw_response_persisted=False,
            warning_messages=warnings,
        )
