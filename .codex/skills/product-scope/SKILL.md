---
name: product-scope
description: Guard the transfer-record timeline MVP scope, user stories, non-diagnostic positioning, and hackathon prioritization. Use when deciding features, copy, architecture trade-offs, or pitch/readme claims.
---

# Transfer Timeline Product Scope

## Goal

Keep all work centered on one verified problem: a receiving clinician needs a fast, traceable overview of a transfer patient's external medical documents before consultation.

## Apply this workflow

1. Read `docs/DEMO_SCOPE.md` before changing product behavior or screen copy.
2. Classify a proposed feature:
   - `MVP core`: upload simulation, OCR/structured fields, timeline aggregation, evidence trace, filters, doctor review.
   - `Demo polish`: loading/error states, visual refinement, demo walkthrough.
   - `Out of scope`: diagnosis, treatment recommendations, HIS/EMR integration, longitudinal chronic care, production authentication.
3. Implement `MVP core` before polish; explicitly defer out-of-scope requests in project notes.
4. Review user-facing language:
   - Say `整理`, `提取`, `待核验`, `材料缺失提示`.
   - Do not say the system `确诊`, `建议治疗`, `判断高风险患者`, or `替代医生`.
5. Ensure each major user action serves the transfer scenario: upload → process → timeline → evidence verification → material-completeness review.

## Completion check

A feature is acceptable only if it improves speed, traceability, or material completeness without presenting unverified output as clinical judgment.
