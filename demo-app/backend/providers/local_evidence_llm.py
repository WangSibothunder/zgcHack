from __future__ import annotations

from typing import Any

from services.external_ai import summarize_from_source


class LocalEvidenceLLMProvider:
    """本地证据检索 LLM provider——基于关键词匹配的 mock 实现。

    不调用外部 API，不消耗额度。在无法连接外部 LLM 时作为保底。
    """

    mode = "mock"
    label = "本地证据检索"

    def rerank_and_summarize(
        self,
        query: str,
        candidate_segments: list[dict[str, Any]],
        retrieval_terms: list[str],
    ) -> list[dict[str, str]]:
        del query
        results: list[dict[str, str]] = []
        for segment in candidate_segments:
            raw_text = str(segment.get("raw_text", ""))
            matched = [term for term in retrieval_terms if term and term.lower() in raw_text.lower()]
            if matched and matched[0] in raw_text:
                relevance_level = "direct_mention"
            elif matched:
                relevance_level = "synonymous_mention"
            else:
                relevance_level = "contextual"
            results.append(
                {
                    "segment_id": str(segment["segment_id"]),
                    "relevance_level": relevance_level,
                    "evidence_summary": summarize_from_source(raw_text, matched[:1]),
                }
            )
        return results
