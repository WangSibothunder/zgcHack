from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from providers.provider_registry import get_provider_status, get_ocr_provider, get_llm_provider_info
from services.evidence_search import list_query_history, rebuild_segments, search_evidence
from services.ingestion import create_ingestion_job, find_anchor, get_job as get_ingestion_job, merge_runtime_nodes
from services.review_store import apply_reviews_to_case, save_review
from services.storage import RUNTIME_DIR, clear_runtime, ensure_runtime_dirs
from services.summary import build_summary

APP_DIR = Path(__file__).resolve().parent
PACK_ROOT = APP_DIR.parent.parent
DATA_DIR = PACK_ROOT / "demo-data"
CASES_DIR = DATA_DIR / "cases"
ASSETS_DIR = DATA_DIR / "assets"
FRONTEND_DIST_DIR = PACK_ROOT / "demo-app" / "frontend" / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "frontend-assets"

NOTICE = "合成演示数据，仅用于材料整理演示，不构成诊断或治疗建议。"
ALLOWED_VERIFICATION_STATUSES = {"unreviewed", "confirmed", "needs_review"}
ensure_runtime_dirs()


class UploadRequest(BaseModel):
    fixture_case_id: str
    file_names: list[str] = Field(default_factory=list, max_length=20)


class ReviewRequest(BaseModel):
    action: str
    corrected_value: str | None = None
    note: str = ""
    reviewer_role: str = "接诊医生（演示）"


class EvidenceSearchRequest(BaseModel):
    case_id: str
    trigger_type: str = "question"
    question: str | None = None
    selected_segment_ids: list[str] = Field(default_factory=list)
    selected_material_id: str | None = None
    selected_text: str | None = None
    top_k: int = Field(default=5, ge=1, le=10)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def load_fixture_case(case_id: str) -> dict[str, Any]:
    path = CASES_DIR / f"{case_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="未找到该合成演示病例。")
    case = load_json(path)
    validate_case(case)
    return case


def load_case(case_id: str) -> dict[str, Any]:
    case = load_fixture_case(case_id)
    case = merge_runtime_nodes(case)
    case = apply_reviews_to_case(case)
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
        case = load_fixture_case(case_id)
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
    confidence = ev.get("confidence")
    if confidence is not None:
        if not 0 <= float(confidence) <= 1:
            raise ValueError("证据 confidence 必须在 0 到 1 之间。")
    # confidence=None 表示 live OCR 未提供置信度，允许通过
    if ev["verification_status"] not in ALLOWED_VERIFICATION_STATUSES:
        raise ValueError(f"未知核验状态: {ev['verification_status']}")


def load_all_cases() -> dict[str, dict[str, Any]]:
    index = validate_index()
    return {item["case_id"]: load_fixture_case(item["case_id"]) for item in index["cases"]}


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_runtime_dirs()
    load_all_cases()
    yield


app = FastAPI(title="转诊迹 Synthetic Demo API", version="0.9.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
app.mount("/runtime-assets", StaticFiles(directory=RUNTIME_DIR), name="runtime-assets")
if FRONTEND_ASSETS_DIR.exists():
    app.mount("/frontend-assets", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="frontend-assets")


@app.get("/", response_model=None)
def frontend_index():
    index_path = FRONTEND_DIST_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {
        "service": "转诊迹 Synthetic Demo API",
        "health": "/health",
        "cases": "/api/v1/demo/cases",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "zhuanzhenji-demo-api", "mode": "synthetic-demo"}


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


@app.post("/api/v2/demo/ingestions")
async def create_ingestion(
    files: list[UploadFile] = File(...),
    case_id: str = Form("demo-cardiac-transfer-001"),
    source: str = Form("upload"),
    synthetic_acknowledged: bool = Form(False),
) -> dict[str, Any]:
    load_case(case_id)
    try:
        return await create_ingestion_job(files, case_id, source, synthetic_acknowledged)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v2/demo/jobs/{job_id}")
def get_ingestion_status(job_id: str) -> dict[str, Any]:
    job = get_ingestion_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="未找到该合成处理任务。")
    return job


@app.get("/api/v2/demo/cases/{case_id}/materials/{material_id}")
def get_v2_material(case_id: str, material_id: str) -> dict[str, Any]:
    return get_material(case_id, material_id)


@app.post("/api/v2/demo/evidence/{anchor_id}/reviews")
def review_evidence(anchor_id: str, payload: ReviewRequest) -> dict[str, Any]:
    cases = [load_case(item["case_id"]) for item in validate_index()["cases"]]
    anchor = next((found for case in cases if (found := find_anchor(case, anchor_id))), None)
    if anchor is None:
        raise HTTPException(status_code=404, detail="未找到该证据字段。")
    try:
        return save_review(anchor_id, payload.model_dump(), anchor["display_value"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v2/demo/cases/{case_id}/summary")
def get_case_summary(case_id: str) -> dict[str, Any]:
    return build_summary(load_case(case_id))


@app.post("/api/v3/demo/cases/{case_id}/segments/rebuild")
def rebuild_case_segments(case_id: str) -> dict[str, Any]:
    try:
        return rebuild_segments(load_case(case_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v3/demo/evidence-search")
def evidence_search(payload: EvidenceSearchRequest) -> dict[str, Any]:
    try:
        return search_evidence(load_case(payload.case_id), payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v3/demo/cases/{case_id}/evidence-search-history")
def evidence_search_history(case_id: str) -> dict[str, Any]:
    load_case(case_id)
    return list_query_history(case_id)


@app.get("/api/v3/demo/providers/status")
def provider_status() -> dict[str, Any]:
    """返回当前 OCR 与 LLM provider 配置状态。"""
    return get_provider_status()


@app.post("/api/v3/demo/providers/vivo/smoke-test")
def vivo_smoke_test() -> dict[str, Any]:
    """测试 vivo provider 配置是否有效。

    注意：本端点仅在 EXTERNAL_AI_ENABLED=true 且配置 vivo provider 时
    才真正调用 vivo API，否则直接返回 mock 模式状态。
    """
    import os

    from providers.vivo_auth import build_vivo_bearer_headers, build_vivo_ocr_headers, redact_sensitive_headers

    app_id = os.getenv("VIVO_APP_ID", "")
    app_key = os.getenv("VIVO_APP_KEY", "")
    if not app_id or not app_key:
        return {
            "configured": False,
            "message": "VIVO_APP_ID 或 VIVO_APP_KEY 未配置，无法执行 smoke test。",
            "ocr": {"provider": "mock", "reachable": None},
            "llm": {"provider": "mock", "reachable": None},
        }

    bearer_headers = build_vivo_bearer_headers()
    ocr_headers = build_vivo_ocr_headers()
    return {
        "configured": True,
        "message": "vivo Bearer 鉴权 header 构造成功。",
        "header_sample": redact_sensitive_headers(bearer_headers),
        "ocr": {
            "provider": "vivo_general_ocr",
            "configured": True,
            "auth_header": "Bearer",
            "content_type": "application/x-www-form-urlencoded",
            "reachable": "pending_manual_test",
        },
        "llm": {
            "provider": "vivo_chat_completions",
            "configured": True,
            "auth_header": "Bearer",
            "reachable": "pending_manual_test",
        },
        "debug_hint": "设置 EXTERNAL_AI_ENABLED=true 后重启服务可启用外部 provider。",
    }


@app.post("/api/v2/demo/runtime/reset")
def reset_runtime() -> dict[str, Any]:
    clear_runtime()
    return {"synthetic": True, "status": "reset", "message": "已清空 synthetic runtime 演示数据。"}
