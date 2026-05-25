from fastapi.testclient import TestClient
from pathlib import Path
import pytest

from app import app
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
    assert len(payload["cases"]) >= 3
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
