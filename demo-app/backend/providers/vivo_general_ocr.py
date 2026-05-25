from __future__ import annotations

import base64
import json
import os
import time
from typing import Any

import httpx

from services.external_ai import assert_synthetic_external_api_allowed
from .base import OCRBlock, OCRResult
from .vivo_auth import build_vivo_sign_headers, redact_sensitive_headers

VIVO_OCR_HOST = "api-ai.vivo.com.cn"
VIVO_OCR_PATH = "/ocr/general_recognition"
DEFAULT_TIMEOUT = 30


class VivoGeneralOCRProvider:
    """vivo 通用 OCR provider。

    连接 vivo AI 平台通用 OCR API，将返回结果映射为统一 OCRResult。

    注意事项：
    - 仅允许处理 synthetic=true 的数据。
    - 若 API 未返回文字坐标，supports_bounding_boxes=False，
      此时不得伪造高亮框。
    - 若获取到 polygon 坐标，会转换为 [x_min, y_min, x_max, y_max] bbox。
    """

    mode = "vivo_general_ocr"
    label = "vivo 通用 OCR"

    def __init__(self) -> None:
        self._host = os.getenv("VIVO_OCR_HOST", VIVO_OCR_HOST)
        self._path = os.getenv("VIVO_OCR_PATH", VIVO_OCR_PATH)
        self._timeout = int(os.getenv("VIVO_OCR_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT)))
        self._business_id = os.getenv("VIVO_OCR_BUSINESS_ID", "")
        self._position_mode = os.getenv("VIVO_OCR_POSITION_MODE", "")

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

        body_dict: dict[str, Any] = {
            "image": image_base64,
            "businessId": self._business_id or "",
        }
        if self._position_mode:
            body_dict["pos"] = self._position_mode

        body_str = json.dumps(body_dict, ensure_ascii=False)
        headers = build_vivo_sign_headers(body=body_str)
        url = f"https://{self._host}{self._path}"

        try:
            resp = httpx.post(
                url,
                headers=headers,
                content=body_str,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
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

        # 根据官方响应结构解析 blocks
        blocks: list[OCRBlock] = []
        raw_blocks = data.get("blocks") or data.get("result", {}).get("blocks") or []
        for index, item in enumerate(raw_blocks):
            if not isinstance(item, dict):
                continue
            block_id = item.get("block_id", f"vivo-ocr-{index:04d}")
            text = item.get("text") or item.get("content") or ""
            confidence = item.get("confidence") or item.get("score")

            # 坐标解析：尝试 polygon 或 bbox
            bbox = None
            polygon: list[list[int]] | None = None

            # 优先四点 polygon
            raw_polygon = item.get("polygon") or item.get("polygons") or item.get("pos")
            if isinstance(raw_polygon, list) and len(raw_polygon) == 4:
                polygon = [[int(p.get("x", 0) if isinstance(p, dict) else p[0]), int(p.get("y", 0) if isinstance(p, dict) else p[1])] for p in raw_polygon]
                xs = [pt[0] for pt in polygon]
                ys = [pt[1] for pt in polygon]
                bbox = [min(xs), min(ys), max(xs), max(ys)]

            # 其次矩形 bbox
            if bbox is None:
                raw_bbox = item.get("bbox") or item.get("rect") or item.get("location")
                if isinstance(raw_bbox, list) and len(raw_bbox) == 4:
                    bbox = [int(raw_bbox[0]), int(raw_bbox[1]), int(raw_bbox[2]), int(raw_bbox[3])]

            blocks.append(OCRBlock(
                block_id=block_id,
                text=str(text),
                bbox=bbox,
                polygon=polygon,
                confidence=float(confidence) if confidence is not None else None,
            ))

        full_text = data.get("full_text") or data.get("text", "") or " ".join(b.text for b in blocks)
        supports_bbox = any(b.bbox is not None for b in blocks)

        return OCRResult(
            provider="vivo_general_ocr",
            provider_label=self.label,
            full_text=full_text,
            blocks=blocks,
            supports_bounding_boxes=supports_bbox,
            synthetic=True,
            raw_response_persisted=False,
        )
