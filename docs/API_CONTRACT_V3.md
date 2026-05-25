# API Contract v3 — Provider Status & vivo Smoke Test

> 在 v0.9 证据联查 API（已实现于 `api/v3/demo/`）基础上，新增 Provider 状态查看与 vivo 连接测试端点。

## GET /api/v3/demo/providers/status

返回当前 OCR 与 LLM provider 的配置、启用状态及其能力。

### 响应（默认 mock 模式）

```json
{
  "synthetic_only": true,
  "ocr": {
    "configured": false,
    "enabled": false,
    "provider": "deterministic_synthetic",
    "label": "预置合成 OCR 回放",
    "supports_bounding_boxes": true,
    "last_smoke_test": "not_run"
  },
  "llm": {
    "configured": false,
    "enabled": false,
    "provider": "mock",
    "label": "本地证据检索",
    "last_smoke_test": "not_run"
  },
  "fallback_available": true,
  "notice": "仅对合成演示材料调用外部能力。"
}
```

### 说明

- `configured`: 环境变量中是否配置了 VIVO_APP_ID/VIVO_APP_KEY
- `enabled`: EXTERNAL_AI_ENABLED=true 且 provider 非 mock
- `supports_bounding_boxes`: 当前 OCR provider 是否返回文字坐标
- `fallback_available`: 外部 API 不可用时是否回退 mock

## POST /api/v3/demo/providers/vivo/smoke-test

测试 vivo 鉴权配置是否有效。

### 响应（未配置）

```json
{
  "configured": false,
  "message": "VIVO_APP_ID 或 VIVO_APP_KEY 未配置，无法执行 smoke test。",
  "ocr": { "provider": "mock", "reachable": null },
  "llm": { "provider": "mock", "reachable": null }
}
```

### 响应（已配置）

```json
{
  "configured": true,
  "message": "vivo 鉴权 header 构造成功。",
  "header_sample": {
    "X-APP-ID": "ABCD...56",
    "X-TIMESTAMP": "1716000000",
    "X-Signature": "abcdef...ef12"
  },
  "ocr": { "provider": "vivo_general_ocr", "reachable": "pending_manual_test" },
  "llm": { "provider": "vivo_bluelm", "reachable": "pending_manual_test" },
  "debug_hint": "设置 EXTERNAL_AI_ENABLED=true 与 VIVO_APP_ID / VIVO_APP_KEY 后重启服务。"
}
```

## 已存在的 v0.9 证据联查 API

### POST /api/v3/demo/evidence-search

**请求：**

```json
{
  "case_id": "demo-evidence-query-appetite-001",
  "trigger_type": "question | selection | field",
  "question": "病人最近的材料中是否提到食欲不振？",
  "selected_segment_ids": [],
  "selected_material_id": null,
  "selected_text": null,
  "top_k": 5
}
```

**响应：** `EvidenceSearchResponse`（见 PRD_V0_9 第 5.4 节）

### POST /api/v3/demo/cases/{case_id}/segments/rebuild

重建病例的可检索片段索引。

### GET /api/v3/demo/cases/{case_id}/evidence-search-history

返回该病例的历史查询记录。
