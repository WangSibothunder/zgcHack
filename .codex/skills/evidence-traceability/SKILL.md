---
name: evidence-traceability
description: Implement verifiable summary-to-source linking, OCR excerpts, confidence presentation, and missing-material reminders in the demo UI and API.
---

# Evidence Traceability Workflow

## Core principle

A structured summary is valuable only when the clinician can return to the source material. Every material-derived claim displayed as a key field must therefore expose its source.

## Minimum evidence model

For each displayed extracted field store:
- `field_key` and `display_value`;
- `material_id`;
- source `page_or_image`;
- `locator_text` and optional placeholder bounding box;
- extraction `confidence`;
- `verification_status` (`unreviewed`, `confirmed`, `needs_review`);
- `is_abnormal_flag`, which describes highlighting only and not diagnosis.

## Frontend behavior

- Clicking a key field opens the evidence panel/modal.
- Show source image, OCR excerpt, locator and confidence together.
- Mark confidence below the contract threshold as `低置信度，待核验`.
- Include a clinician-facing control or visible state for confirmed/needs-review in the demo.
- Display material-completeness notices separately from extracted medical fields.

## Backend/test behavior

- Ensure all evidence references resolve to a material.
- Ensure evidence payload never omits confidence or source locator.
- Add a test that traverses the cardiac case and confirms all key evidence references are valid.

## Wording rule

Use evidence language (`原图定位`, `OCR 置信度`, `待核验`) rather than reasoning language (`系统判断`, `诊断为`, `建议治疗`).
