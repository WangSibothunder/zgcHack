---
name: synthetic-medical-data
description: Create or edit safe fictional patient fixtures and mock material assets for the medical-record demo without introducing real patient information or ungrounded clinical claims.
---

# Synthetic Demo Data Authoring

## Rules

Every generated case must:
- state `synthetic: true`;
- include a visible safety notice;
- use fictional hospital and patient identifiers;
- contain no real names, phone numbers, national IDs, addresses, barcodes, QR codes or imported reports;
- use simplified mock values solely to demonstrate extraction and timeline interactions;
- phrase status as `待医生核验` when a field is marked abnormal.

## Fixture structure

Each case should contain:
- transfer context and reason;
- chronological `timeline_nodes`;
- per-node materials;
- OCR excerpt;
- structured fields;
- evidence anchors with confidence;
- optional missing-material reminders;
- UI tags/filter metadata.

## Content strategy

Use three synthetic scenarios to demonstrate generality without expanding the MVP:
1. cardiology transfer: recurrent chest discomfort and outside test material chronology;
2. neurology transfer: imaging-report chronology and incomplete material reminder;
3. oncology transfer: pathology/report and treatment-summary material chronology.

These are not used for medical advice and must not promise medical conclusions.

## Asset strategy

Mock source-material thumbnails may be SVG/PNG cards labelled `合成演示材料`. They may contain invented lines matching fixture OCR excerpts, so the evidence modal has a credible visual anchor.

## Validation

Before commit, grep for unexpected identifiers and validate that every material referenced by a node has a corresponding mock asset or explicit placeholder path.
