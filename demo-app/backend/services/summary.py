from __future__ import annotations

from typing import Any

from .review_store import list_reviews


def build_summary(case: dict[str, Any]) -> dict[str, Any]:
    reviews = {review["anchor_id"]: review for review in list_reviews()}
    anchors = [
        anchor
        for node in case.get("timeline_nodes", [])
        for anchor in node.get("evidence_anchors", [])
    ]
    confirmed = 0
    needs_review = 0
    corrected = 0
    for anchor in anchors:
        review = reviews.get(anchor["anchor_id"])
        if review and review["action"] == "confirmed":
            confirmed += 1
        elif review and review["action"] == "corrected":
            corrected += 1
            needs_review += 1
        elif review and review["action"] == "needs_review":
            needs_review += 1
        elif anchor.get("verification_status") == "confirmed":
            confirmed += 1
        else:
            needs_review += 1
    uploaded_count = sum(
        1
        for material in case.get("materials", {}).values()
        if material.get("processing_source") == "现场合成材料处理"
    )
    return {
        "synthetic": True,
        "notice": case["notice"],
        "case_id": case["case_id"],
        "patient_display": f"{case['patient']['display_name']}，{case['patient']['sex']}，{case['patient']['age_display']}（合成演示患者）",
        "transfer_path": f"{case['transfer']['origin_hospital']} → {case['transfer']['destination_hospital']}｜{case['transfer']['destination_department']}",
        "coverage": case["transfer"]["coverage"],
        "node_count": len(case.get("timeline_nodes", [])),
        "uploaded_material_count": uploaded_count,
        "transfer_related_nodes": [
            {"date": node["date"], "headline": node["headline"], "document_type": node["document_type"]}
            for node in case.get("timeline_nodes", [])
            if node.get("related_to_transfer_reason")
        ],
        "review_counts": {
            "confirmed": confirmed,
            "needs_review": needs_review,
            "corrected": corrected,
            "unreviewed": max(len(anchors) - confirmed - needs_review, 0),
        },
        "missing_material_reminders": [
            f"{item} 未发现相关材料时，请人工核对是否需要补充。"
            for item in case.get("missing_material_reminders", [])
        ],
        "boundary": "系统仅整理材料和证据，不生成诊断或治疗意见。",
    }
