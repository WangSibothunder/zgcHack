from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from .image_quality import evaluate_quality, validate_upload_name_and_size
from .storage import GENERATED_CASES_DIR, JOBS_DIR, UPLOADS_DIR, read_json, write_json
from .synthetic_ocr_provider import recognize_from_sidecar

PROCESSING_MODE = "live_synthetic_upload"
OCR_MODE_LABEL = "预置合成 OCR 演示回放"


async def create_ingestion_job(
    files: list[UploadFile],
    case_id: str,
    source: str,
    synthetic_acknowledged: bool,
) -> dict[str, Any]:
    if not synthetic_acknowledged:
        raise ValueError("必须确认仅上传合成演示材料。")
    if not files:
        raise ValueError("请至少选择一张合成演示材料。")
    if len(files) > 10:
        raise ValueError("单次最多上传 10 张合成演示材料。")
    if source not in {"upload", "camera"}:
        raise ValueError("source 仅支持 upload 或 camera。")

    job_id = f"ingest-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    upload_dir = UPLOADS_DIR / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    materials: list[dict[str, Any]] = []
    generated_node_ids: list[str] = []
    has_retake = False
    for index, upload in enumerate(files):
        content = await upload.read()
        filename = safe_filename(upload.filename or f"synthetic-upload-{index}.png")
        validate_upload_name_and_size(filename, content)
        path = upload_dir / filename
        path.write_bytes(content)
        quality = evaluate_quality(filename, content)
        if quality["status"] == "retake_required":
            has_retake = True
            materials.append(
                {
                    "source_file": filename,
                    "stored_path": str(path),
                    "quality": quality,
                    "status": "retake_required",
                }
            )
            continue
        ocr = recognize_from_sidecar(path)
        material = build_runtime_material(job_id, index, filename, path, quality, ocr, source)
        node = build_runtime_node(job_id, index, material, ocr, source)
        materials.append(material)
        write_json(GENERATED_CASES_DIR / f"{job_id}-{index}.json", {"case_id": case_id, "node": node, "material": material})
        generated_node_ids.append(node["node_id"])

    status = "retake_required" if has_retake and not generated_node_ids else "timeline_generated"
    steps = build_steps(status)
    job = {
        "job_id": job_id,
        "synthetic": True,
        "status": status,
        "processing_mode": PROCESSING_MODE,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generated_case_id": case_id,
        "generated_node_ids": generated_node_ids,
        "materials": materials,
        "steps": steps,
        "message": "合成演示材料已接收，开始处理。" if status != "retake_required" else "图片质量不足，请重新拍摄或上传清晰合成材料。",
    }
    write_json(JOBS_DIR / f"{job_id}.json", job)
    return job


def get_job(job_id: str) -> dict[str, Any] | None:
    path = JOBS_DIR / f"{job_id}.json"
    if not path.exists():
        return None
    return read_json(path)


def merge_runtime_nodes(case: dict[str, Any]) -> dict[str, Any]:
    generated = []
    for path in sorted(GENERATED_CASES_DIR.glob("*.json")):
        payload = read_json(path)
        if payload.get("case_id") == case.get("case_id"):
            generated.append(payload)
    if not generated:
        return case
    materials = dict(case.get("materials", {}))
    nodes = list(case.get("timeline_nodes", []))
    for item in generated:
        material = item["material"]
        node = item["node"]
        materials[material["material_id"]] = material
        existing = next((current for current in nodes if current["date"] == node["date"]), None)
        if existing:
            existing["materials"].append(material["material_id"])
            existing["structured_fields"].update(node["structured_fields"])
            existing["evidence_anchors"].extend(node["evidence_anchors"])
            existing["tags"] = merge_tags(existing.get("tags", []), node.get("tags", []))
            existing["summary"] = "同日追加现场合成材料处理结果，字段均待医生核验。"
            existing["processing_source"] = "现场合成材料处理"
        else:
            nodes.append(node)
    case["materials"] = materials
    case["timeline_nodes"] = sorted(nodes, key=lambda node: node["date"])
    case["available_filters"]["document_types"] = sorted(
        set(case["available_filters"].get("document_types", [])) | {node["document_type"] for node in nodes}
    )
    return case


def find_anchor(case: dict[str, Any], anchor_id: str) -> dict[str, Any] | None:
    for node in case.get("timeline_nodes", []):
        for anchor in node.get("evidence_anchors", []):
            if anchor.get("anchor_id") == anchor_id:
                return anchor
    return None


def build_runtime_material(
    job_id: str,
    index: int,
    filename: str,
    path: Path,
    quality: dict[str, Any],
    ocr: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    material_id = f"runtime-mat-{job_id}-{index}"
    anchor_id = f"ev-live-{job_id}-{index}"
    highlight = ocr.get("source_highlights", ["原文标记字段"])[0]
    marker_block = next((block for block in ocr["blocks"] if "肌钙蛋白" in block["text"]), ocr["blocks"][0])
    anchor = {
        "anchor_id": anchor_id,
        "field_key": "原文标记字段",
        "display_value": f"{highlight}（原材料标记，待核验）",
        "material_id": material_id,
        "page_or_image": "现场合成材料，第 1 张",
        "locator_text": marker_block["text"],
        "confidence": marker_block["confidence"],
        "ocr_confidence": marker_block["confidence"],
        "extraction_confidence": 0.9,
        "verification_status": "unreviewed",
        "is_abnormal_flag": True,
        "ocr_block_ids": [marker_block["block_id"]],
        "bbox": marker_block["bbox"],
        "source_mode": PROCESSING_MODE,
    }
    return {
        "material_id": material_id,
        "title": "现场合成检验材料",
        "image_url": f"/runtime-assets/uploads/{job_id}/{filename}",
        "ocr_text": ocr["full_text"],
        "ocr_mode": ocr.get("ocr_mode", "deterministic_synthetic"),
        "ocr_mode_label": OCR_MODE_LABEL,
        "ocr_blocks": ocr["blocks"],
        "quality": quality,
        "processing_source": "现场合成材料处理",
        "source": source,
        "evidence_anchors": [anchor],
    }


def build_runtime_node(
    job_id: str,
    index: int,
    material: dict[str, Any],
    ocr: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    document_date = ocr.get("document_date", "2025-01-17")
    node_id = f"runtime-node-{document_date}-{job_id}-{index}"
    anchor = material["evidence_anchors"][0]
    return {
        "node_id": node_id,
        "date": document_date,
        "hospital_department": f"{ocr.get('hospital_name', '青禾县中心医院（虚构）')}｜{ocr.get('department', '检验科')}",
        "document_type": ocr.get("document_type", "检验报告"),
        "headline": "现场合成材料处理结果",
        "summary": "系统整理上传的合成材料，提取原文标记字段并绑定原图证据框。",
        "tags": [
            {"label": "新上传", "level": "success"},
            {"label": "现场合成材料处理", "level": "info"},
            {"label": "异常字段待核验", "level": "warning"},
        ],
        "related_to_transfer_reason": bool(ocr.get("transfer_related_text")),
        "has_abnormal_flag": True,
        "materials": [material["material_id"]],
        "structured_fields": {
            "报告日期": document_date,
            "材料类型": ocr.get("document_type", "检验报告"),
            "原文标记字段": anchor["display_value"],
            "处理来源": "摄像头采集" if source == "camera" else "文件上传",
        },
        "ocr_excerpt": ocr["full_text"],
        "processing_source": "现场合成材料处理",
        "evidence_anchors": [anchor],
    }


def build_steps(status: str) -> list[dict[str, str]]:
    if status == "retake_required":
        return [
            {"name": "文件接收", "status": "completed"},
            {"name": "图像质量检测", "status": "retake_required"},
            {"name": "OCR 识别", "status": "blocked"},
            {"name": "字段抽取", "status": "blocked"},
            {"name": "时间轴生成", "status": "blocked"},
        ]
    return [
        {"name": "文件接收", "status": "completed"},
        {"name": "图像质量检测", "status": "completed"},
        {"name": "OCR 识别", "status": "completed", "mode": "deterministic_synthetic"},
        {"name": "字段抽取", "status": "completed"},
        {"name": "时间轴生成", "status": "completed"},
    ]


def merge_tags(existing: list[dict[str, str]], incoming: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = {tag["label"] for tag in existing}
    merged = list(existing)
    for tag in incoming:
        if tag["label"] not in seen:
            merged.append(tag)
            seen.add(tag["label"])
    return merged


def safe_filename(filename: str) -> str:
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9_.\-\u4e00-\u9fff]", "_", name)
