---
name: frontend-timeline
description: Implement and polish the horizontally scrollable medical record timeline UI from the provided visual prototype, while consuming backend API data and preserving evidence interactions.
---

# Frontend Timeline Implementation

## Source of truth

Use `reference/transfer_medical_timeline_mockup.html` as the visual and interaction baseline:
- header contains transfer context;
- timeline shows material thumbnails above the axis and structured summaries below it;
- selection updates a detail side panel;
- evidence view exposes original material, OCR, confidence, and field source.

Do not ship a page whose data remains embedded in a `const records = [...]` block. Data must be loaded through the API adapter.

## Implementation procedure

1. Inspect existing frontend stack; preserve it if usable. If there is no app scaffold, create a minimal Vite React TypeScript app.
2. Create typed models for `CaseSummary`, `TimelineResponse`, `TimelineNode`, `Material`, and `EvidenceAnchor`, matching `docs/API_CONTRACT.md`.
3. Add an API client with configurable API base URL.
4. Build the view states:
   - case selection / default demo case;
   - loading skeleton;
   - timeline loaded;
   - empty;
   - API failure with retry;
   - low-confidence evidence marker.
5. Build interaction:
   - chronological horizontal timeline;
   - active node detail panel;
   - node filters;
   - evidence modal;
   - simulated upload progress and completed case redirect.
6. Surface safety labels persistently in header/detail or footer.

## UI acceptance

- At desktop width, timeline and detail panel remain readable.
- At mobile/narrow width, the interface stacks without losing evidence functionality.
- Keyboard focus and clear buttons exist for node/evidence interaction.
- Filtered nodes preserve chronological order.
- Original document thumbnails resolve from the backend/static API rather than from unrelated external URLs.

## Verification

Run frontend build/type checks/tests, then manually test all interactions with the cardiac fixture and at least one other fixture.
