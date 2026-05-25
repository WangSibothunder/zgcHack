from __future__ import annotations

from pathlib import Path
from typing import Any

from .storage import PACK_ROOT, read_json

SIDECAR_DIR = PACK_ROOT / "demo-data" / "capture-samples" / "sidecars"


def recognize_from_sidecar(image_path: Path) -> dict[str, Any]:
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
