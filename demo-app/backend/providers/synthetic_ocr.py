from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import OCRBlock, OCRResult

SIDECAR_DIR = Path(__file__).resolve().parents[2] / "demo-data" / "capture-samples" / "sidecars"


def recognize_from_sidecar(image_path: Path) -> dict[str, Any]:
    """从 sidecar JSON 读取预置 OCR 结果。"""
    from services.storage import read_json

    sidecar_path = SIDECAR_DIR / f"{image_path.stem}.ocr.json"
    if sidecar_path.exists():
        return read_json(sidecar_path)
    return {
        "ocr_mode": "deterministic_synthetic",
        "blocks": [
            {
                "block_id": "ocr-default-date",
                "text": "报告日期：2025-01-17",
                "bbox": [80, 110, 430, 150],
                "confidence": 0.94,
            },
            {
                "block_id": "ocr-default-marker",
                "text": "肌钙蛋白 I：0.19 ng/mL ↑",
                "bbox": [88, 290, 560, 338],
                "confidence": 0.9,
            },
        ],
        "full_text": "合成演示材料｜报告日期：2025-01-17｜肌钙蛋白 I：0.19 ng/mL ↑｜建议转上级医院进一步评估。",
        "document_date": "2025-01-17",
        "hospital_name": "青禾县中心医院（虚构）",
        "department": "检验科",
        "document_type": "检验报告",
        "source_highlights": ["肌钙蛋白 I：0.19 ng/mL ↑"],
        "transfer_related_text": "建议转上级医院进一步评估",
    }


class SyntheticOCRProvider:
    """确定性合成 OCR provider——从 sidecar 或硬编码 fallback 读取。"""

    mode = "deterministic_synthetic"
    label = "预置合成 OCR 回放"

    def recognize(self, image_path: str | None = None, image_bytes: bytes | None = None) -> OCRResult:
        if image_path:
            path = Path(image_path)
            sidecar = recognize_from_sidecar(path)
        else:
            sidecar = recognize_from_sidecar(Path("cardiac_lab_clear.png"))

        blocks = [
            OCRBlock(
                block_id=block.get("block_id", f"syn-{index}"),
                text=block.get("text", ""),
                bbox=block.get("bbox"),
                confidence=block.get("confidence"),
            )
            for index, block in enumerate(sidecar.get("blocks", []))
        ]
        return OCRResult(
            provider="deterministic_synthetic",
            provider_label=self.label,
            full_text=sidecar.get("full_text", ""),
            blocks=blocks,
            supports_bounding_boxes=any(b.bbox is not None for b in blocks),
            synthetic=True,
        )


def is_synthetic_ocr_mode(payload: dict[str, Any]) -> bool:
    """判断 OCR 模式是否为确定性合成回放。"""
    return payload.get("ocr_mode") == "deterministic_synthetic"
