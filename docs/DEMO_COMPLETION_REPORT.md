# Demo Completion Report

## 环境与启动方式

- Frontend stack: Vite + React + TypeScript + Playwright.
- Backend stack: FastAPI + Pydantic + pytest.
- Frontend run command: `cd demo-app/frontend && npm install && npm run dev -- --port 5173`.
- Backend run command: `cd demo-app/backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app:app --host 127.0.0.1 --port 8000`.
- Date of verification: 2026-05-25, Asia/Shanghai.

## Acceptance Evidence

| Item | Status | Command / manual verification / screenshot |
| --- | --- | --- |
| Synthetic notice visible | PASS | `npm run smoke` checks visible notice text: `合成演示数据，仅用于材料整理演示，不构成诊断或治疗建议。` |
| Three fixture cases selectable | PASS | `curl http://127.0.0.1:8000/api/v1/demo/cases` returns 3 cases; frontend case selector loads all 3. |
| Cardiac case six nodes sorted | PASS | `pytest -q` verifies cardiac node count is 6 and dates are sorted; Playwright checks first and last node dates. |
| Detail/evidence/modal flow | PASS | `npm run smoke` clicks a cardiac node, opens an evidence item, and verifies the evidence dialog. |
| Filters | PASS | `npm run smoke` verifies abnormal-only and document-type filters; UI also exposes transfer-related and empty-result filters. |
| Upload simulation | PASS | `curl -X POST /api/v1/demo/uploads` returned completed job `job-demo-cardiac-transfer-001`; `npm run smoke` verifies completed UI flow. |
| Loading/error/empty/low confidence | PASS | Loading/error/empty UI implemented; `npm run smoke` verifies empty-result and neuro low-confidence state `低置信度，待核验｜OCR 82%`. |
| API tests | PASS | `cd demo-app/backend && .venv/bin/python -m pytest -q` -> `8 passed in 0.19s`. |
| Frontend build/tests | PASS | `npm run lint && npm run typecheck && npm test && npm run build && npm run smoke` -> lint/typecheck pass, Vitest `4 passed`, Vite build pass, Playwright `2 passed`. |
| Secret/PHI scan | PASS | `.gitignore` excludes envs, venv, node_modules, dist, reports, uploads and real-data folders; final tracked-file scan found no `.env`, credentials, or real patient materials. |

## Demo Walkthrough

1. Start backend on `127.0.0.1:8000` and frontend on `127.0.0.1:5173`.
2. Open the page and confirm the synthetic/non-diagnostic notice.
3. Use the case selector to switch between cardiac, neurology and oncology synthetic transfer cases.
4. In the cardiac case, horizontally browse 6 chronological nodes; thumbnails sit above the axis and summaries sit below it.
5. Click a node to update the detail panel with structured fields, OCR, evidence entries, confidence and material previews.
6. Click an evidence entry to open the original synthetic material with locator text and OCR confidence.
7. Apply abnormal-only, transfer-related and document-type filters; use empty-result demo for empty-state feedback.
8. Click simulated upload and confirm the completed job links back to a generated synthetic case.

## Synthetic-Only Boundary

- All case data and source material images are under `demo-data/` and marked `synthetic: true`.
- UI and API wording states `仅用于材料整理演示，不构成诊断或治疗建议`.
- The upload flow accepts fixture case IDs and demo file names only; it does not process real patient files or claim real OCR.

## GitHub Delivery

- Repository name: `zgcHack`.
- Visibility: public, per current `转诊迹` public synthetic demo policy.
- Local commit SHA: `0cde353` for `feat: deliver synthetic transfer timeline demo`; a follow-up report commit records this delivery status.
- Push command output: previously blocked locally because `gh auth status` returned `zsh:1: command not found: gh`. Install GitHub CLI and authenticate, then push to the existing public repository following `docs/GITHUB_DELIVERY.md`.
