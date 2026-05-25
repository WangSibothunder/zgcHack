from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
PACK_ROOT = APP_DIR.parent.parent
DATA_DIR = PACK_ROOT / "demo-data"
CASES_DIR = DATA_DIR / "cases"
ASSETS_DIR = DATA_DIR / "assets"

NOTICE = "合成演示数据，仅用于材料整理演示，不构成诊断或治疗建议。"
ALLOWED_VERIFICATION_STATUSES = {"unreviewed", "confirmed", "needs_review"}


class UploadRequest(BaseModel):
    fixture_case_id: str
    file_names: list[str] = Field(default_factory=list, max_length=20)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def load_case(case_id: str) -> dict[str, Any]:
    path = CASES_DIR / f"{case_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="未找到该合成演示病例。")
    case = load_json(path)
    validate_case(case)
    return case


def validate_index() -> dict[str, Any]:
    index = load_json(CASES_DIR / "index.json")
    if index.get("synthetic") is not True or index.get("notice") != NOTICE:
        raise ValueError("病例索引必须包含 synthetic=true 与标准安全提示。")
    seen: set[str] = set()
    for item in index.get("cases", []):
        case_id = item.get("case_id")
        if not case_id or case_id in seen:
            raise ValueError(f"病例 ID 缺失或重复: {case_id}")
        seen.add(case_id)
        case = load_case(case_id)
        if item.get("node_count") != len(case.get("timeline_nodes", [])):
            raise ValueError(f"病例索引节点数不一致: {case_id}")
        abnormal_count = sum(1 for node in case["timeline_nodes"] if node.get("has_abnormal_flag"))
        if item.get("abnormal_flag_count") != abnormal_count:
            raise ValueError(f"病例索引异常标记数不一致: {case_id}")
    if len(seen) < 3:
        raise ValueError("Demo 至少需要三个合成病例。")
    return index


def validate_case(case: dict[str, Any]) -> None:
    if case.get("synthetic") is not True or case.get("notice") != NOTICE:
        raise ValueError("Demo fixture 必须包含 synthetic=true 与安全提示。")
    materials = case.get("materials", {})
    if not materials:
        raise ValueError("病例必须包含材料字典。")
    previous: date | None = None
    node_ids: set[str] = set()
    for node in case.get("timeline_nodes", []):
        node_id = node.get("node_id")
        if not node_id or node_id in node_ids:
            raise ValueError(f"节点 ID 缺失或重复: {node_id}")
        node_ids.add(node_id)
        current = date.fromisoformat(node["date"])
        if previous and current < previous:
            raise ValueError("时间轴节点未按日期升序排列。")
        previous = current
        for material_id in node.get("materials", []):
            if material_id not in materials:
                raise ValueError(f"节点引用了不存在的材料: {material_id}")
        for ev in node.get("evidence_anchors", []):
            validate_evidence(ev, materials)
    for material_id, material in materials.items():
        if material.get("material_id") != material_id:
            raise ValueError(f"材料 ID 与字典键不一致: {material_id}")
        image_url = material.get("image_url", "")
        if not image_url.startswith("/assets/"):
            raise ValueError(f"材料图片必须来自合成静态资源: {material_id}")
        asset_path = ASSETS_DIR / image_url.removeprefix("/assets/")
        if not asset_path.exists():
            raise ValueError(f"材料图片文件不存在: {asset_path}")
        for ev in material.get("evidence_anchors", []):
            validate_evidence(ev, materials)


def validate_evidence(ev: dict[str, Any], materials: dict[str, Any]) -> None:
    material_id = ev.get("material_id")
    if material_id not in materials:
        raise ValueError(f"证据引用了不存在的材料: {material_id}")
    required = [
        "anchor_id",
        "field_key",
        "display_value",
        "page_or_image",
        "locator_text",
        "confidence",
        "verification_status",
        "is_abnormal_flag",
    ]
    missing = [key for key in required if key not in ev]
    if missing:
        raise ValueError(f"证据字段缺失: {','.join(missing)}")
    if not 0 <= float(ev["confidence"]) <= 1:
        raise ValueError("证据 confidence 必须在 0 到 1 之间。")
    if ev["verification_status"] not in ALLOWED_VERIFICATION_STATUSES:
        raise ValueError(f"未知核验状态: {ev['verification_status']}")


def load_all_cases() -> dict[str, dict[str, Any]]:
    index = validate_index()
    return {item["case_id"]: load_case(item["case_id"]) for item in index["cases"]}


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_all_cases()
    yield


app = FastAPI(title="zgcHack Synthetic Demo API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "zgcHack-demo-api", "mode": "synthetic-demo"}


@app.get("/api/v1/demo/cases")
def list_cases() -> dict[str, Any]:
    return validate_index()


@app.get("/api/v1/demo/cases/{case_id}/timeline")
def timeline(case_id: str) -> dict[str, Any]:
    return load_case(case_id)


@app.get("/api/v1/demo/cases/{case_id}/materials/{material_id}")
def get_material(case_id: str, material_id: str) -> dict[str, Any]:
    case = load_case(case_id)
    material = case["materials"].get(material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="未找到该合成材料。")
    return {"synthetic": True, "notice": NOTICE, **material}


@app.post("/api/v1/demo/uploads")
def simulate_upload(payload: UploadRequest) -> dict[str, Any]:
    load_case(payload.fixture_case_id)
    return {
        "job_id": f"job-{payload.fixture_case_id}",
        "status": "completed",
        "synthetic": True,
        "generated_case_id": payload.fixture_case_id,
        "file_count": len(payload.file_names),
        "message": "合成材料处理完成，已生成演示时间轴。",
    }


@app.get("/api/v1/demo/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    prefix = "job-"
    if not job_id.startswith(prefix):
        raise HTTPException(status_code=404, detail="未找到该演示任务。")
    case_id = job_id[len(prefix):]
    load_case(case_id)
    return {
        "job_id": job_id,
        "status": "completed",
        "synthetic": True,
        "generated_case_id": case_id,
        "message": "合成材料处理完成，已生成演示时间轴。",
    }
