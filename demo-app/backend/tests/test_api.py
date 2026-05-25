from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


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
