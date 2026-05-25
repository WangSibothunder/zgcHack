from fastapi.testclient import TestClient
from pathlib import Path
import pytest

from app import app
from services.external_ai import ExternalOCRApiProvider, SyntheticExternalApiError, assert_synthetic_external_api_allowed
from services.evidence_search import merge_llm_results
from services.storage import clear_runtime

client = TestClient(app)
PACK_ROOT = Path(__file__).resolve().parents[3]
SAMPLES = PACK_ROOT / "demo-data" / "capture-samples"


@pytest.fixture(autouse=True)
def reset_runtime_between_tests() -> None:
    clear_runtime()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["mode"] == "synthetic-demo"


def test_case_list_is_synthetic_and_has_three_cases() -> None:
    payload = client.get("/api/v1/demo/cases").json()
    assert payload["synthetic"] is True
    assert len(payload["cases"]) >= 4
    assert len({case["case_id"] for case in payload["cases"]}) == len(payload["cases"])


def test_cardiac_timeline_is_sorted_and_traceable() -> None:
    response = client.get("/api/v1/demo/cases/demo-cardiac-transfer-001/timeline")
    assert response.status_code == 200
    payload = response.json()
    nodes = payload["timeline_nodes"]
    assert len(nodes) == 6
    dates = [node["date"] for node in nodes]
    assert dates == sorted(dates)
    assert payload["synthetic"] is True
    for node in nodes:
        for ev in node["evidence_anchors"]:
            assert ev["material_id"] in payload["materials"]
            assert "confidence" in ev
            assert "page_or_image" in ev
            assert "locator_text" in ev
            assert ev["verification_status"] in {"unreviewed", "confirmed", "needs_review"}


def test_all_fixtures_are_sorted_synthetic_and_reference_complete() -> None:
    cases = client.get("/api/v1/demo/cases").json()["cases"]
    for item in cases:
        response = client.get(f"/api/v1/demo/cases/{item['case_id']}/timeline")
        assert response.status_code == 200
        payload = response.json()
        assert payload["synthetic"] is True
        assert "不构成诊断或治疗建议" in payload["notice"]
        dates = [node["date"] for node in payload["timeline_nodes"]]
        assert dates == sorted(dates)
        assert item["node_count"] == len(payload["timeline_nodes"])
        for node in payload["timeline_nodes"]:
            assert node["materials"]
            for material_id in node["materials"]:
                material = payload["materials"][material_id]
                assert material["image_url"].startswith("/assets/")
                asset_response = client.get(material["image_url"])
                assert asset_response.status_code == 200
            for evidence in node["evidence_anchors"]:
                assert evidence["material_id"] in payload["materials"]
                assert evidence["page_or_image"]
                assert evidence["locator_text"]
                assert 0 <= evidence["confidence"] <= 1


def test_cardiac_key_evidence_matches_material_payloads() -> None:
    payload = client.get("/api/v1/demo/cases/demo-cardiac-transfer-001/timeline").json()
    for node in payload["timeline_nodes"]:
        for evidence in node["evidence_anchors"]:
            material = client.get(
                f"/api/v1/demo/cases/{payload['case_id']}/materials/{evidence['material_id']}"
            ).json()
            anchors = {anchor["anchor_id"]: anchor for anchor in material["evidence_anchors"]}
            assert evidence["anchor_id"] in anchors
            assert anchors[evidence["anchor_id"]]["locator_text"] == evidence["locator_text"]


def test_material_endpoint_and_upload_simulation() -> None:
    material = client.get(
        "/api/v1/demo/cases/demo-cardiac-transfer-001/materials/mat-card-20250115-lab"
    )
    assert material.status_code == 200
    assert material.json()["evidence_anchors"][0]["confidence"] == 0.91

    job = client.post(
        "/api/v1/demo/uploads",
        json={
            "fixture_case_id": "demo-cardiac-transfer-001",
            "file_names": ["合成材料-1.pdf", "合成材料-2.jpg"],
        },
    )
    assert job.status_code == 200
    assert job.json()["generated_case_id"] == "demo-cardiac-transfer-001"


def test_unknown_case_returns_404() -> None:
    response = client.get("/api/v1/demo/cases/not-present/timeline")
    assert response.status_code == 404


def test_unknown_job_returns_404() -> None:
    response = client.get("/api/v1/demo/jobs/job-not-present")
    assert response.status_code == 404


def test_v2_rejects_upload_without_synthetic_acknowledgement() -> None:
    sample = SAMPLES / "originals" / "cardiac_lab_clear.png"
    with sample.open("rb") as fp:
        response = client.post(
            "/api/v2/demo/ingestions",
            data={"case_id": "demo-cardiac-transfer-001", "source": "upload", "synthetic_acknowledged": "false"},
            files={"files": ("cardiac_lab_clear.png", fp, "image/png")},
        )
    assert response.status_code == 400
    assert "合成演示材料" in response.json()["detail"]


def test_v2_rejects_unsupported_format() -> None:
    response = client.post(
        "/api/v2/demo/ingestions",
        data={"case_id": "demo-cardiac-transfer-001", "source": "upload", "synthetic_acknowledged": "true"},
        files={"files": ("not-supported.txt", b"synthetic", "text/plain")},
    )
    assert response.status_code == 400
    assert "仅支持" in response.json()["detail"]


def test_v2_blurred_sample_requires_retake() -> None:
    client.post("/api/v2/demo/runtime/reset")
    sample = SAMPLES / "degraded" / "cardiac_lab_blurred.png"
    with sample.open("rb") as fp:
        response = client.post(
            "/api/v2/demo/ingestions",
            data={"case_id": "demo-cardiac-transfer-001", "source": "upload", "synthetic_acknowledged": "true"},
            files={"files": ("cardiac_lab_blurred.png", fp, "image/png")},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "retake_required"
    assert payload["materials"][0]["quality"]["status"] == "retake_required"
    assert not payload["generated_node_ids"]


def test_v2_clear_sample_generates_timeline_material_and_bbox_evidence() -> None:
    client.post("/api/v2/demo/runtime/reset")
    sample = SAMPLES / "originals" / "cardiac_lab_clear.png"
    with sample.open("rb") as fp:
        response = client.post(
            "/api/v2/demo/ingestions",
            data={"case_id": "demo-cardiac-transfer-001", "source": "upload", "synthetic_acknowledged": "true"},
            files={"files": ("cardiac_lab_clear.png", fp, "image/png")},
        )
    assert response.status_code == 200
    job = response.json()
    assert job["status"] == "timeline_generated"
    assert job["steps"][-1]["status"] == "completed"
    timeline = client.get("/api/v1/demo/cases/demo-cardiac-transfer-001/timeline").json()
    runtime_nodes = [node for node in timeline["timeline_nodes"] if node.get("processing_source") == "现场合成材料处理"]
    assert runtime_nodes
    evidence = runtime_nodes[0]["evidence_anchors"][0]
    assert evidence["bbox"] == [96, 310, 610, 366]
    material = client.get(
        f"/api/v2/demo/cases/demo-cardiac-transfer-001/materials/{evidence['material_id']}"
    ).json()
    assert material["ocr_mode"] == "deterministic_synthetic"
    assert material["quality"]["status"] == "pass"


def test_v2_review_persists_and_summary_counts_update() -> None:
    client.post("/api/v2/demo/runtime/reset")
    sample = SAMPLES / "originals" / "cardiac_lab_clear.png"
    with sample.open("rb") as fp:
        job = client.post(
            "/api/v2/demo/ingestions",
            data={"case_id": "demo-cardiac-transfer-001", "source": "upload", "synthetic_acknowledged": "true"},
            files={"files": ("cardiac_lab_clear.png", fp, "image/png")},
        ).json()
    timeline = client.get("/api/v1/demo/cases/demo-cardiac-transfer-001/timeline").json()
    runtime_node = next(node for node in timeline["timeline_nodes"] if job["generated_node_ids"][0] == node["node_id"])
    anchor_id = runtime_node["evidence_anchors"][0]["anchor_id"]
    review = client.post(
        f"/api/v2/demo/evidence/{anchor_id}/reviews",
        json={"action": "confirmed", "note": "演示确认", "reviewer_role": "接诊医生（演示）"},
    )
    assert review.status_code == 200
    assert review.json()["synthetic"] is True
    refreshed = client.get("/api/v1/demo/cases/demo-cardiac-transfer-001/timeline").json()
    refreshed_anchor = next(
        anchor
        for node in refreshed["timeline_nodes"]
        for anchor in node["evidence_anchors"]
        if anchor["anchor_id"] == anchor_id
    )
    assert refreshed_anchor["verification_status"] == "confirmed"
    summary = client.get("/api/v2/demo/cases/demo-cardiac-transfer-001/summary").json()
    assert summary["review_counts"]["confirmed"] >= 1
    assert summary["uploaded_material_count"] >= 1


def test_v3_rebuilds_segments_for_appetite_case() -> None:
    response = client.post("/api/v3/demo/cases/demo-evidence-query-appetite-001/segments/rebuild")
    assert response.status_code == 200
    payload = response.json()
    assert payload["synthetic"] is True
    assert payload["segment_count"] == 4
    assert payload["index_mode"] == "json_substring_with_synonym_fallback"


def test_v3_appetite_question_recalls_synonym_segments_with_bbox() -> None:
    response = client.post(
        "/api/v3/demo/evidence-search",
        json={
            "case_id": "demo-evidence-query-appetite-001",
            "trigger_type": "question",
            "question": "病人最近的材料中是否提到食欲不振？",
            "top_k": 5,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    excerpts = [item["source_excerpt"] for item in payload["items"]]
    assert "食欲不振" in "".join(excerpts)
    assert "食欲欠佳" in "".join(excerpts)
    assert "纳差" in "".join(excerpts)
    assert "WBC" not in "".join(excerpts)
    assert payload["not_found_note"] is None
    assert all(item["material_id"] and item["node_id"] and item["segment_id"] for item in payload["items"])
    assert all(item["bbox"] for item in payload["items"])
    assert all(item["anchor_id"] for item in payload["items"])


def test_v3_cardiac_question_recalls_partial_chest_term() -> None:
    response = client.post(
        "/api/v3/demo/evidence-search",
        json={
            "case_id": "demo-cardiac-transfer-001",
            "trigger_type": "question",
            "question": "胸部",
            "top_k": 5,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert "胸部不适" in "".join(item["source_excerpt"] for item in payload["items"])
    assert "胸部" in payload["retrieval_terms"]


def test_v3_no_result_uses_safe_boundary_copy() -> None:
    response = client.post(
        "/api/v3/demo/evidence-search",
        json={
            "case_id": "demo-evidence-query-appetite-001",
            "trigger_type": "question",
            "question": "材料中是否记录睡眠打鼾？",
            "top_k": 5,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert "未检索到明确相关记载" in payload["result_statement"]
    assert "不代表患者不存在该情况" in payload["not_found_note"]


def test_v3_selection_search_excludes_current_material_and_records_history() -> None:
    response = client.post(
        "/api/v3/demo/evidence-search",
        json={
            "case_id": "demo-evidence-query-appetite-001",
            "trigger_type": "selection",
            "selected_material_id": "mat-appetite-20250109-followup",
            "selected_text": "患者近一周食欲欠佳，进食量较前减少。",
            "top_k": 5,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert all(item["material_id"] != "mat-appetite-20250109-followup" for item in payload["items"])
    history = client.get("/api/v3/demo/cases/demo-evidence-query-appetite-001/evidence-search-history").json()
    assert history["queries"]
    assert history["queries"][0]["result_segment_ids"]


def test_external_ocr_mapping_marks_bbox_support() -> None:
    mapped = ExternalOCRApiProvider().map_response(
        {
            "blocks": [
                {"text": "食欲不振", "bbox": [1, 2, 30, 40], "confidence": 0.93},
                {"text": "纯文本行", "confidence": 0.8},
            ]
        }
    )
    assert mapped["supports_bounding_boxes"] is True
    assert mapped["blocks"][0]["bbox"] == [1, 2, 30, 40]
    assert mapped["blocks"][1]["bbox"] is None


def test_external_api_rejects_non_synthetic_payload() -> None:
    with pytest.raises(SyntheticExternalApiError):
        assert_synthetic_external_api_allowed({"synthetic": False})


def test_unknown_llm_segment_ids_are_dropped() -> None:
    segments = [
        {
            "segment_id": "seg-known",
            "material_id": "mat-1",
            "node_id": "node-1",
            "anchor_id": "ev-1",
            "document_date": "2025-01-01",
            "document_type": "门诊病历",
            "raw_text": "食欲不振",
            "bboxes": [[1, 2, 3, 4]],
            "ocr_confidence": 0.9,
            "verification_status": "unreviewed",
        }
    ]
    items = merge_llm_results(
        [{"segment_id": "seg-missing", "relevance_level": "direct_mention", "evidence_summary": "不应出现"}],
        segments,
        ["食欲不振"],
        3,
        "mock",
    )
    assert len(items) == 1
    assert items[0]["segment_id"] == "seg-known"
