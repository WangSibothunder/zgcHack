# API Contract v2：转诊迹 Synthetic Ingestion Demo

Base path: `/api/v2/demo`

所有 v2 接口仅用于合成演示材料。响应必须带 `synthetic: true`，不得声称处理真实病例。

## POST /ingestions

`multipart/form-data`

- `files`: `.png`、`.jpg`、`.jpeg`，最多 10 张，每张最大 10 MB。
- `case_id`: 目标合成病例 ID。
- `source`: `upload` 或 `camera`。
- `synthetic_acknowledged`: 必须为 `true`。

返回处理任务、质量检测结果、OCR fallback 模式和生成节点 ID。`retake_required` 不进入 OCR。

## GET /jobs/{job_id}

返回任务状态和步骤：

- `uploaded`
- `retake_required`
- `timeline_generated`
- `failed`

Demo 当前使用 `deterministic_synthetic`，界面展示为“预置合成 OCR 演示回放”。

## GET /cases/{case_id}/materials/{material_id}

返回材料详情，包含：

- `image_url`
- `quality`
- `ocr_mode`
- `ocr_blocks`
- `evidence_anchors[].bbox`
- `evidence_anchors[].verification_status`

旧版 fixture 若无 bbox，可继续返回文字定位。

## POST /evidence/{anchor_id}/reviews

请求：

```json
{
  "action": "confirmed | needs_review | corrected",
  "corrected_value": "action=corrected 时必填",
  "note": "核验说明",
  "reviewer_role": "接诊医生（演示）"
}
```

review 写入 `demo-app/backend/runtime/reviews/`，该目录必须被 Git 忽略。

## GET /cases/{case_id}/summary

返回接诊前整理摘要：患者合成标识、转院路径、材料覆盖、节点数量、现场上传材料数量、核验计数、转院相关节点和材料完整性提示。摘要只来自时间轴结构化数据和 review 状态，不生成诊断或治疗建议。

## POST /runtime/reset

清空 synthetic runtime 演示数据，便于重复演示和自动化测试。
