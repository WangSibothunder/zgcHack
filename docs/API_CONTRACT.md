# Demo API Contract v1

API base path: `/api/v1/demo`

所有响应必须带有合成数据标识或由页面持续显示安全提示。时间统一使用 ISO `YYYY-MM-DD` 格式。

## 1. Health

`GET /health`

```json
{"status":"ok","service":"zgcHack-demo-api","mode":"synthetic-demo"}
```

## 2. Case list

`GET /api/v1/demo/cases`

```json
{
  "synthetic": true,
  "notice": "合成演示数据，仅用于材料整理演示，不构成诊断或治疗建议。",
  "cases": [
    {
      "case_id": "demo-cardiac-transfer-001",
      "patient_display": "演示患者 A01，男，62 岁",
      "destination_department": "心内科",
      "transfer_reason": "反复胸部不适，需进一步核验外院材料",
      "node_count": 6,
      "abnormal_flag_count": 5
    }
  ]
}
```

## 3. Timeline detail

`GET /api/v1/demo/cases/{case_id}/timeline`

Response keys:

| Field | Meaning |
| --- | --- |
| `synthetic` | Must be `true` in demo. |
| `notice` | Persistent non-diagnostic notice. |
| `case_id` | Stable case identifier. |
| `patient` | Display-only fictional patient information. |
| `transfer` | Origin/destination/reason/coverage. |
| `timeline_nodes` | Chronological nodes, each corresponding to one date. |
| `available_filters` | Frontend filter metadata. |
| `missing_material_reminders` | Organizational reminders only. |

A `timeline_node` contains:

```json
{
  "node_id": "node-2025-01-15",
  "date": "2025-01-15",
  "hospital_department": "青禾县中心医院｜心内科",
  "document_type": "门诊病历 + 化验单 + 心电图报告",
  "headline": "复诊记录与转院材料整理",
  "summary": "记录中存在待核验的指标标记，并记载建议到上级医院进一步评估。",
  "tags": [{"label":"转院相关","level":"info"},{"label":"异常字段待核验","level":"warning"}],
  "related_to_transfer_reason": true,
  "has_abnormal_flag": true,
  "materials": ["mat-card-20250115-lab", "mat-card-20250115-note"],
  "structured_fields": [],
  "ocr_excerpt": "……",
  "evidence_anchors": []
}
```

## 4. Material detail

`GET /api/v1/demo/cases/{case_id}/materials/{material_id}`

```json
{
  "synthetic": true,
  "material_id": "mat-card-20250115-lab",
  "title": "合成化验单",
  "image_url": "/assets/cardiac-001/2025-01-15-lab.svg",
  "ocr_text": "合成演示材料……",
  "evidence_anchors": [
    {
      "anchor_id": "ev-card-tni",
      "field_key": "关键指标",
      "display_value": "肌钙蛋白 I：0.19 ng/mL（标记升高，待核验）",
      "page_or_image": "第 1 张，第 3 行",
      "locator_text": "肌钙蛋白 I",
      "confidence": 0.91,
      "verification_status": "unreviewed",
      "is_abnormal_flag": true
    }
  ]
}
```

## 5. Upload simulation

`POST /api/v1/demo/uploads`

Demo 阶段不处理真实病例。请求体只接受 synthetic fixture selector：

```json
{"fixture_case_id":"demo-cardiac-transfer-001","file_names":["合成材料-1.pdf","合成材料-2.jpg"]}
```

Response:

```json
{
  "job_id": "job-demo-cardiac-transfer-001",
  "status": "completed",
  "synthetic": true,
  "generated_case_id": "demo-cardiac-transfer-001",
  "message": "合成材料处理完成，已生成演示时间轴。"
}
```

## 6. Job status

`GET /api/v1/demo/jobs/{job_id}` returns the same job state. Unknown identifiers return HTTP 404 with a human-readable detail.

## Status/UX constraints

- 前端对 HTTP error 必须显示可恢复的失败状态。
- `confidence < 0.85` 的 evidence 应显示低置信度待核验提示。
- 所有“缺失材料”内容为整理提醒，不得表达医学必要性或诊疗判断。
