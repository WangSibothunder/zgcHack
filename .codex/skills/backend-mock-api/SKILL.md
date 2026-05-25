---
name: backend-mock-api
description: Build or modify the separate demo backend and JSON fixture API for synthetic transfer cases, timeline nodes, materials, evidence and simulated upload jobs.
---

# Backend Mock API Workflow

## Purpose

Provide a deterministic backend for the hackathon demo. It represents OCR and extraction as already processed synthetic fixture data, rather than pretending to run a medical AI pipeline.

## Required inputs

- `demo-data/cases/index.json`
- `demo-data/cases/*.json`
- `demo-data/assets/**`
- `docs/API_CONTRACT.md`

## Implementation procedure

1. Keep all application routes under `/api/v1/demo/`; add `GET /health`.
2. Load and validate JSON fixtures at application startup.
3. Validate:
   - case IDs are unique;
   - node dates parse and are non-decreasing;
   - node/material/evidence references resolve;
   - `synthetic` is true and safety notice is present.
4. Implement endpoints for list, timeline and material detail.
5. Implement deterministic upload simulation:
   - accept metadata or placeholder files;
   - return a job identifier;
   - job status advances or immediately resolves to a known synthetic case;
   - no OCR is claimed unless an OCR module actually exists.
6. Enable frontend local-development CORS only for configured local origins.
7. Add tests for health, happy paths, missing ID, chronological nodes and upload job.

## Do not do

- Do not introduce a real patient upload pathway during Demo.
- Do not connect to external health APIs.
- Do not store files containing real health data.
- Do not describe seeded OCR text as generated from a real patient record.

## Done output

Document endpoint commands and test results in `docs/DEMO_COMPLETION_REPORT.md`.
