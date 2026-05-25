# 说明

Codex 官方识别的仓库指令文件名是 `AGENTS.md`。本文件保留以满足团队内部称呼；请以同目录的 `AGENTS.md` 作为执行入口。


# zgcHack Repository Instructions

## 1. Product mission and non-negotiable boundary

This repository builds a hackathon demo for **transfer-patient medical record timeline reconstruction**. A patient arrives at a new hospital with external paper records or report screenshots. The system organizes those records into a chronological, evidence-traceable timeline so a receiving clinician can review prior context faster.

The product is **not** a diagnostic system, treatment recommender, triage engine, or medical decision maker. Never phrase UI text, API responses, README claims, or pitch material as medical diagnosis or treatment guidance.

During the demo phase, use **synthetic fixtures only**. Never introduce real personally identifiable health information, real patient images, real medical identifiers, or copied hospital documents.

## 2. Demo definition of done

The demo is complete only when all of the following are demonstrably working:

- A frontend and a backend run separately and communicate through HTTP API calls.
- A demo case list exposes at least three synthetic transfer cases.
- The cardiac transfer case reproduces the existing design intent: one date per node, original-material thumbnail above the axis, structured summary below it, detail panel, OCR text, evidence location, and missing-material notice.
- The timeline is horizontally browsable and nodes are chronologically sorted.
- Filters work for at least: all nodes, abnormal-only, document type, and transfer-reason-related.
- Clicking a node updates detail data fetched from or represented by the API payload.
- Clicking a material/evidence item opens an evidence view with a source image and highlighted or textual locator.
- A mock upload/processing flow exists: selected demo files create a job, reach a completed state, and link to a generated demo case.
- Every clinical-looking screen shows a clear synthetic-data and non-diagnostic notice.
- Loading, empty, API-failure, and low-confidence states are visible and usable.
- README contains exact local run commands; automated smoke tests pass; a short demo script is present.

Read `docs/DEMO_ACCEPTANCE.md` for the acceptance checklist and do not declare completion until each checkbox has executable proof.

## 3. Working method

Before editing:
1. Inspect the actual repository tree, package manager, existing frontend stack, and current scripts.
2. Preserve the uploaded visual prototype as the design baseline; migrate hard-coded case records behind an API rather than discarding interaction decisions.
3. Read `docs/API_CONTRACT.md`, `docs/SYNTHETIC_DATA_POLICY.md`, and relevant skills under `.codex/skills/`.

Implementation order:
1. Establish or confirm repository structure and run commands.
2. Add/confirm backend API and load `demo-data/` fixtures.
3. Connect frontend to API; preserve timeline and evidence UX.
4. Implement filtering, upload simulation, states, and safety notices.
5. Add tests, seed validation, README, and demo walkthrough.
6. Only after acceptance passes, initialize/push the repository to GitHub following `docs/GITHUB_DELIVERY.md`.

When blocked, do not stop after describing the issue. Diagnose it, implement the smallest safe correction, rerun checks, and update the evidence log.

## 4. Architecture conventions

Prefer the repository's existing technology choices. If the uploaded prototype is the only application code and no stack is established, use:

- Frontend: Vite + React + TypeScript.
- Backend: FastAPI + Pydantic.
- Demo data: JSON fixtures under `demo-data/`.
- Testing: frontend unit/smoke testing appropriate to the selected stack and backend `pytest`.

Keep front and back end separate:

- Frontend must not contain the full timeline fixture as application state except fallback test mocks.
- Backend owns case, timeline, material, OCR and evidence payloads.
- Static synthetic material assets may be served by the backend or a clearly configured static asset base URL.
- All API paths should be versioned below `/api/v1/demo/`.

## 5. Required API behaviors

Implement the endpoints defined in `docs/API_CONTRACT.md`. Do not silently change response shape: update docs, fixtures, frontend adapter, and tests in the same commit.

Essential endpoints:

- `GET /health`
- `GET /api/v1/demo/cases`
- `GET /api/v1/demo/cases/{case_id}/timeline`
- `GET /api/v1/demo/cases/{case_id}/materials/{material_id}`
- `POST /api/v1/demo/uploads`
- `GET /api/v1/demo/jobs/{job_id}`

## 6. Medical data and UX safeguards

- Use labels such as `合成演示数据` and `仅用于材料整理演示，不构成诊断或治疗建议`.
- Use `异常字段待核验` rather than implying a confirmed medical judgment.
- Evidence must identify material, page/image, field/line or bounding-box placeholder, and OCR confidence.
- Low-confidence extraction must be visually marked.
- Missing-material output must be phrased as an organizational reminder, never as clinical necessity.
- Never upload or commit secrets, account tokens, real documents, `.env` values, or local cache data.

## 7. Code quality and testing

- Prefer typed interfaces/models for API payloads.
- Validate fixture schema and chronological ordering.
- Handle API errors explicitly in UI.
- Avoid large unreviewed dependency additions; prefer maintained dependencies already in the project.
- After each meaningful change, run relevant formatting, type checks, tests, and a local browser smoke pass.
- Capture the final commands and results in `docs/DEMO_COMPLETION_REPORT.md`.

## 8. Git and delivery rules

- Make small coherent commits with meaningful messages.
- Do not rewrite or delete the supplied prototype without preserving it under `reference/`.
- Default the GitHub repository to **private** because the project concerns medical-document workflows, even though demo records are synthetic.
- Do not push until tests and the demo acceptance checklist pass.
- Before pushing, run a secret scan or at minimum inspect tracked files for tokens, `.env`, credentials, and unintended personal data.
- The intended final repository name is `zgcHack`.

## 9. Codex skills to use

Use these repository skills when relevant:

- `$product-scope` for product decisions and feature trade-offs.
- `$frontend-timeline` for timeline UI and visual prototype alignment.
- `$backend-mock-api` for API/fixtures/backend changes.
- `$synthetic-medical-data` before creating or modifying demo records/assets.
- `$evidence-traceability` for OCR/evidence/confidence/detail-view behavior.
- `$demo-delivery-loop` for integration, QA, completion evidence, and GitHub delivery.
