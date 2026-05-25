from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .storage import REVIEWS_DIR, list_json, read_json, write_json

ALLOWED_REVIEW_ACTIONS = {"confirmed", "needs_review", "corrected"}


def save_review(anchor_id: str, payload: dict[str, Any], before_value: str) -> dict[str, Any]:
    action = payload.get("action")
    if action not in ALLOWED_REVIEW_ACTIONS:
        raise ValueError("核验操作仅支持 confirmed、needs_review、corrected。")
    if action == "corrected" and not payload.get("corrected_value"):
        raise ValueError("修改字段时必须填写 corrected_value。")
    after_value = payload.get("corrected_value") if action == "corrected" else before_value
    review = {
        "review_id": f"review-{anchor_id}",
        "anchor_id": anchor_id,
        "action": action,
        "before_value": before_value,
        "after_value": after_value,
        "note": payload.get("note", ""),
        "reviewer_role": payload.get("reviewer_role", "接诊医生（演示）"),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "synthetic": True,
    }
    write_json(REVIEWS_DIR / f"{anchor_id}.json", review)
    return review


def get_review(anchor_id: str) -> dict[str, Any] | None:
    path = REVIEWS_DIR / f"{anchor_id}.json"
    if not path.exists():
        return None
    return read_json(path)


def list_reviews() -> list[dict[str, Any]]:
    return list_json(REVIEWS_DIR)


def apply_reviews_to_case(case: dict[str, Any]) -> dict[str, Any]:
    reviews = {review["anchor_id"]: review for review in list_reviews()}
    if not reviews:
        return case
    for node in case.get("timeline_nodes", []):
        for evidence in node.get("evidence_anchors", []):
            apply_review_to_anchor(evidence, reviews)
    for material in case.get("materials", {}).values():
        for evidence in material.get("evidence_anchors", []):
            apply_review_to_anchor(evidence, reviews)
    return case


def apply_review_to_anchor(anchor: dict[str, Any], reviews: dict[str, dict[str, Any]]) -> None:
    review = reviews.get(anchor.get("anchor_id"))
    if not review:
        return
    action = review["action"]
    anchor["verification_status"] = "confirmed" if action == "confirmed" else "needs_review"
    if action == "corrected":
        anchor["verification_status"] = "needs_review"
        anchor["display_value"] = review["after_value"]
        anchor["corrected_value"] = review["after_value"]
        anchor["correction_note"] = review.get("note", "")
