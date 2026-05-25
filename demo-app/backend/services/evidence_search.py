from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from providers.provider_registry import get_llm_provider
from services.external_ai import summarize_from_source
from services.storage import EVIDENCE_INDEX_DIR, EVIDENCE_QUERIES_DIR, list_json, read_json, write_json

NOTICE = "以上为合成材料中的相关证据归纳，不构成诊断或治疗建议。"
NOT_FOUND_NOTE = "这仅表示现有材料中未找到相关证据，不代表患者不存在该情况。"

SYNONYMS: dict[str, list[str]] = {
    "食欲不振": ["食欲欠佳", "纳差", "进食减少", "进食量减少", "进食量较前减少"],
    "胸痛": ["胸部", "胸部不适", "胸闷", "胸前区不适", "胸前区疼痛"],
    "转院": ["转上级医院", "上级医院进一步评估", "转诊", "进一步诊治"],
    "肌钙蛋白": ["cTnI", "TnI", "肌钙蛋白 I"],
    "ST-T": ["心电图", "ST-T 改变", "复查"],
    "缺失材料": ["未见", "冠脉 CTA", "造影", "材料提示"],
}

RELEVANCE_LABELS = {
    "direct_mention": "直接提及",
    "synonymous_mention": "同义表述",
    "contextual": "上下文相关",
}


def rebuild_segments(case: dict[str, Any]) -> dict[str, Any]:
    if case.get("synthetic") is not True:
        raise ValueError("证据联查索引仅允许 synthetic=true 的合成演示病例。")
    segments = build_segments(case)
    payload = {
        "case_id": case["case_id"],
        "segment_count": len(segments),
        "index_mode": "json_substring_with_synonym_fallback",
        "synthetic": True,
        "segments": segments,
        "rebuilt_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(_index_path(case["case_id"]), payload)
    return {key: payload[key] for key in ["case_id", "segment_count", "index_mode", "synthetic"]}


def build_segments(case: dict[str, Any]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    materials = case.get("materials", {})
    for node in case.get("timeline_nodes", []):
        hospital, department = _split_hospital_department(node.get("hospital_department", ""))
        for material_id in node.get("materials", []):
            material = materials.get(material_id)
            if not material:
                continue
            material_anchors = material.get("evidence_anchors", [])
            ocr_blocks = material.get("ocr_blocks") or []
            if ocr_blocks:
                for index, block in enumerate(ocr_blocks, start=1):
                    anchor = _find_anchor_for_block(block.get("block_id"), material_anchors) or (material_anchors[0] if material_anchors else {})
                    segment = _segment_from_source(
                        case_id=case["case_id"],
                        node=node,
                        material=material,
                        hospital=hospital,
                        department=department,
                        text=block.get("text") or anchor.get("display_value") or material.get("ocr_text", ""),
                        ocr_block_ids=[block.get("block_id")] if block.get("block_id") else [],
                        bboxes=[block.get("bbox") or anchor.get("bbox")] if block.get("bbox") or anchor.get("bbox") else [],
                        confidence=block.get("confidence") or anchor.get("ocr_confidence") or anchor.get("confidence") or 0,
                        anchor=anchor,
                        suffix=f"{index:03d}",
                    )
                    segments.append(segment)
            else:
                if material.get("ocr_text"):
                    anchor = material_anchors[0] if material_anchors else {}
                    segments.append(
                        _segment_from_source(
                            case_id=case["case_id"],
                            node=node,
                            material=material,
                            hospital=hospital,
                            department=department,
                            text=material.get("ocr_text", ""),
                            ocr_block_ids=anchor.get("ocr_block_ids", []),
                            bboxes=[anchor["bbox"]] if anchor.get("bbox") else [],
                            confidence=anchor.get("ocr_confidence") or anchor.get("confidence") or 0,
                            anchor=anchor,
                            suffix="ocr-text",
                        )
                    )
                for index, anchor in enumerate(material_anchors, start=1):
                    text = anchor.get("display_value") or anchor.get("locator_text") or material.get("ocr_text", "")
                    segments.append(
                        _segment_from_source(
                            case_id=case["case_id"],
                            node=node,
                            material=material,
                            hospital=hospital,
                            department=department,
                            text=text,
                            ocr_block_ids=anchor.get("ocr_block_ids", []),
                            bboxes=[anchor["bbox"]] if anchor.get("bbox") else [],
                            confidence=anchor.get("ocr_confidence") or anchor.get("confidence") or 0,
                            anchor=anchor,
                            suffix=f"{index:03d}",
                        )
                    )
    return segments


def search_evidence(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if case.get("synthetic") is not True:
        raise ValueError("证据联查仅允许 synthetic=true 的合成演示病例。")
    segments = load_or_build_segments(case)
    query_text = (payload.get("question") or payload.get("selected_text") or "").strip()
    retrieval_terms = expand_terms(query_text)
    excluded_segment_ids = set(payload.get("selected_segment_ids") or [])
    selected_material_id = payload.get("selected_material_id")
    candidates = [
        (segment, score_segment(segment, retrieval_terms, query_text))
        for segment in segments
        if segment["segment_id"] not in excluded_segment_ids
    ]
    if payload.get("trigger_type") in {"selection", "field"} and selected_material_id:
        candidates = [(segment, score) for segment, score in candidates if segment["material_id"] != selected_material_id]
    candidates = [(segment, score) for segment, score in candidates if score > 0]
    candidates.sort(key=lambda item: (-item[1], _reverse_date_key(str(item[0].get("document_date") or "")), item[0]["segment_id"]))
    top_k = int(payload.get("top_k") or 5)
    candidate_segments = [segment for segment, _ in candidates[: max(top_k * 4, top_k)]]

    provider = get_llm_provider()
    try:
        llm_items = provider.rerank_and_summarize(query_text, candidate_segments, retrieval_terms)
    except Exception:
        llm_items = []
        provider_mode = "unavailable_fallback"
    else:
        provider_mode = provider.mode

    items = merge_llm_results(llm_items, candidate_segments, retrieval_terms, top_k, provider_mode)
    result_statement = (
        f"在当前已上传的合成材料中找到 {len(items)} 条相关记录。"
        if items
        else "在当前已上传材料中未检索到明确相关记载。"
    )
    query_id = f"query-{uuid4().hex[:12]}"
    response = {
        "query_id": query_id,
        "case_id": case["case_id"],
        "answer_mode": "evidence_only",
        "query_display": query_display(retrieval_terms, query_text),
        "retrieval_terms": retrieval_terms,
        "result_statement": result_statement,
        "items": items,
        "not_found_note": None if items else NOT_FOUND_NOTE,
        "llm_mode": provider_mode if provider_mode != "mock" else "mock",
        "notice": NOTICE,
        "synthetic": True,
    }
    save_query_history(case["case_id"], payload, response)
    return response


def load_or_build_segments(case: dict[str, Any]) -> list[dict[str, Any]]:
    path = _index_path(case["case_id"])
    if not path.exists():
        rebuild_segments(case)
    return read_json(path).get("segments", [])


def list_query_history(case_id: str) -> dict[str, Any]:
    rows = [
        item
        for item in list_json(EVIDENCE_QUERIES_DIR)
        if item.get("case_id") == case_id and item.get("synthetic") is True
    ]
    rows.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return {"case_id": case_id, "synthetic": True, "queries": rows}


def save_query_history(case_id: str, request_payload: dict[str, Any], response: dict[str, Any]) -> None:
    row = {
        "query_id": response["query_id"],
        "case_id": case_id,
        "trigger_type": request_payload.get("trigger_type", "question"),
        "question": request_payload.get("question"),
        "selected_material_id": request_payload.get("selected_material_id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider_mode": response["llm_mode"],
        "result_segment_ids": [item["segment_id"] for item in response["items"]],
        "synthetic": True,
    }
    write_json(EVIDENCE_QUERIES_DIR / f"{row['query_id']}.json", row)


def expand_terms(text: str) -> list[str]:
    terms: list[str] = []
    normalized = normalize_text(text)
    for canonical, synonyms in SYNONYMS.items():
        candidates = [canonical, *synonyms]
        if any(normalize_text(term) in normalized for term in candidates):
            terms.extend(candidates)
    if not terms:
        for token in _fallback_tokens(text):
            if token not in terms:
                terms.append(token)
    return _dedupe(terms)


def score_segment(segment: dict[str, Any], terms: list[str], query_text: str) -> int:
    searchable = normalize_text(f"{segment.get('raw_text', '')} {segment.get('normalized_text', '')}")
    score = 0
    for term in terms:
        normalized_term = normalize_text(term)
        if normalized_term and normalized_term in searchable:
            score += 4 if normalized_term in normalize_text(segment.get("raw_text", "")) else 2
    for token in _fallback_tokens(query_text):
        if token and token in searchable:
            score += 1
    return score


def merge_llm_results(
    llm_items: list[dict[str, str]],
    candidate_segments: list[dict[str, Any]],
    retrieval_terms: list[str],
    top_k: int,
    provider_mode: str,
) -> list[dict[str, Any]]:
    segment_by_id = {segment["segment_id"]: segment for segment in candidate_segments}
    rows: list[tuple[dict[str, Any], str, str]] = []
    seen: set[str] = set()
    for item in llm_items:
        segment_id = item.get("segment_id")
        if not segment_id or segment_id not in segment_by_id or segment_id in seen:
            continue
        seen.add(segment_id)
        rows.append(
            (
                segment_by_id[segment_id],
                item.get("relevance_level", "contextual"),
                item.get("evidence_summary", "")[:90],
            )
        )
    for segment in candidate_segments:
        if len(rows) >= top_k:
            break
        if segment["segment_id"] in seen:
            continue
        matched = [term for term in retrieval_terms if normalize_text(term) in normalize_text(segment.get("raw_text", ""))]
        rows.append((segment, infer_relevance(segment, retrieval_terms), summarize_from_source(segment["raw_text"], matched[:1])))
        seen.add(segment["segment_id"])
    return [item_from_segment(index, segment, relevance, summary, provider_mode) for index, (segment, relevance, summary) in enumerate(rows[:top_k], start=1)]


def item_from_segment(rank: int, segment: dict[str, Any], relevance_level: str, summary: str, provider_mode: str) -> dict[str, Any]:
    relevance = relevance_level if relevance_level in RELEVANCE_LABELS else "contextual"
    first_bbox = segment.get("bboxes", [None])[0] if segment.get("bboxes") else None
    return {
        "rank": rank,
        "relevance_level": relevance,
        "relevance_label": RELEVANCE_LABELS[relevance],
        "material_id": segment["material_id"],
        "node_id": segment["node_id"],
        "segment_id": segment["segment_id"],
        "anchor_id": segment.get("anchor_id"),
        "document_date": segment.get("document_date"),
        "document_type": segment.get("document_type"),
        "hospital_name": segment.get("hospital_name"),
        "department": segment.get("department"),
        "source_excerpt": segment["raw_text"],
        "evidence_summary": summary or summarize_from_source(segment["raw_text"], []),
        "bbox": first_bbox,
        "ocr_confidence": segment.get("ocr_confidence", 0),
        "ranking_source": "keyword+mock_rerank" if provider_mode == "mock" else "local_keyword_fallback",
        "verification_status": segment.get("verification_status", "unreviewed"),
    }


def infer_relevance(segment: dict[str, Any], terms: list[str]) -> str:
    raw = normalize_text(segment.get("raw_text", ""))
    for canonical, synonyms in SYNONYMS.items():
        group = [canonical, *synonyms]
        group_matched_query = any(term in terms for term in group)
        if group_matched_query and normalize_text(canonical) in raw:
            return "direct_mention"
        if group_matched_query and any(normalize_text(term) in raw for term in synonyms):
            return "synonymous_mention"
    return "contextual"


def normalize_text(text: object) -> str:
    return str(text or "").replace(" ", "").replace("，", ",").replace("。", ".").lower()


def query_display(terms: list[str], query_text: str) -> str:
    if terms:
        return f"{terms[0]}相关记录"
    return query_text[:30] or "相关记录"


def _segment_from_source(
    *,
    case_id: str,
    node: dict[str, Any],
    material: dict[str, Any],
    hospital: str | None,
    department: str | None,
    text: str,
    ocr_block_ids: list[str],
    bboxes: list[list[int]],
    confidence: float,
    anchor: dict[str, Any],
    suffix: str,
) -> dict[str, Any]:
    anchor_id = anchor.get("anchor_id") or f"anchor-{suffix}"
    return {
        "segment_id": f"seg-{case_id}-{node['node_id']}-{anchor_id}-{suffix}",
        "case_id": case_id,
        "node_id": node["node_id"],
        "material_id": material["material_id"],
        "anchor_id": anchor.get("anchor_id"),
        "page_number": 1,
        "document_date": node.get("date"),
        "document_type": node.get("document_type"),
        "hospital_name": hospital,
        "department": department,
        "author_text": None,
        "raw_text": text,
        "normalized_text": normalize_text(text),
        "ocr_block_ids": ocr_block_ids,
        "bboxes": bboxes,
        "ocr_confidence": float(confidence or 0),
        "synthetic": True,
        "source_mode": material.get("ocr_mode") or anchor.get("source_mode") or "deterministic_synthetic",
        "verification_status": anchor.get("verification_status", "unreviewed"),
    }


def _find_anchor_for_block(block_id: str | None, anchors: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not block_id:
        return None
    return next((anchor for anchor in anchors if block_id in anchor.get("ocr_block_ids", [])), None)


def _split_hospital_department(text: str) -> tuple[str | None, str | None]:
    parts = [part.strip() for part in text.split("｜") if part.strip()]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    return (parts[0], None) if parts else (None, None)


def _fallback_tokens(text: str) -> list[str]:
    stopwords = ["病人", "患者", "最近", "材料", "是否", "提到", "当前", "记录", "哪些", "何时", "中", "的", "？", "?"]
    cleaned = text
    for word in stopwords:
        cleaned = cleaned.replace(word, " ")
    return [token for token in cleaned.replace("，", " ").replace("。", " ").split() if len(token) >= 2]


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _reverse_date_key(value: str) -> int:
    digits = "".join(ch for ch in value if ch.isdigit())
    return -int(digits or "0")


def _index_path(case_id: str) -> Path:
    return EVIDENCE_INDEX_DIR / f"{case_id}.json"
