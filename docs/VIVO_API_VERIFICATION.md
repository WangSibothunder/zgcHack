# vivo AI 平台 API 接入验证报告（模板）

## 1. 目标

验证 `providers/vivo_general_ocr.py` 与 `providers/vivo_bluelm_evidence.py` 的适配器
是否能够正确连接 vivo AI 平台 API，并将返回结果映射为统一的 `OCRResult` 与 `LLMGroundedResult`。

## 2. 前置条件

- [ ] 已从 [vivo AIGC 创新赛平台](https://aigc.vivo.com.cn/) 申请到 APP_ID 与 APP_KEY。
- [ ] 已确认使用的 API 端点：
  - OCR: `/ocr/general_recognition`（或实际分配的端点）
  - BlueLM: `/v1/chat/completions`（或实际分配的端点）
- [ ] 已在 `.env` 中填写：

```bash
EXTERNAL_AI_ENABLED=true
OCR_PROVIDER=vivo_general_ocr
LLM_PROVIDER=vivo_bluelm
VIVO_APP_ID=您的APP_ID
VIVO_APP_KEY=您的APP_KEY
```

## 3. OCR API 验证

### 3.1 使用 Smoke Test 端点

```bash
curl -X POST http://localhost:8000/api/v3/demo/providers/vivo/smoke-test
```

预期返回：

```json
{
  "configured": true,
  "message": "vivo 鉴权 header 构造成功。",
  "header_sample": { "X-APP-ID": "ABCD...56", "X-TIMESTAMP": "...", "X-Signature": "abcdef...ef12" }
}
```

### 3.2 直接调用 OCR API

使用 Python 脚本或 curl 向 vivo 通用 OCR 发送一张合成图片：

```python
import requests, base64, hmac, hashlib, json, time

app_id = "your_app_id"
app_key = "your_app_key"
image_b64 = base64.b64encode(open("demo-data/assets/evidence-query-001/2025-01-09-followup.svg", "rb").read()).decode()
body = json.dumps({"image": image_b64, "businessId": ""})

timestamp = int(time.time())
sign = hmac.new(app_key.encode(), f"{body}{timestamp}".encode(), hashlib.sha256).hexdigest()
headers = {"Content-Type": "application/json", "X-APP-ID": app_id, "X-TIMESTAMP": str(timestamp), "X-Signature": sign}

resp = requests.post("https://api-ai.vivo.com.cn/ocr/general_recognition", data=body, headers=headers)
print(resp.status_code, resp.text[:500])
```

验证项目：
- [ ] HTTP 200 响应
- [ ] 响应中包含 `blocks` 列表
- [ ] 至少一个 block 包含 `text`、`confidence`
- [ ] 是否返回 `polygon`/`bbox`/`pos` 坐标（决定 `supports_bounding_boxes`）
- [ ] 中文识别准确率
- [ ] 文件大小限制

### 3.3 书面向导决定

如果 OCR API **返回 bbox** → `supports_bounding_boxes=True`，可用于原图高亮。
如果 OCR API **只返回纯文本** → `supports_bounding_boxes=False`，保留 sidecar bbox 演示路径，
UI 中说明"该 API 模式下仅能回到材料页，无法定位到文字框"。

## 4. BlueLM API 验证

### 4.1 验证 BlueLM 端点兼容性

用 Python 脚本直接测试：

```python
import requests, json, hmac, hashlib, time

app_id = "your_app_id"
app_key = "your_app_key"
body = json.dumps({
    "model": "BlueLM",
    "messages": [{"role": "user", "content": "你好"}]
})

timestamp = int(time.time())
sign = hmac.new(app_key.encode(), f"{body}{timestamp}".encode(), hashlib.sha256).hexdigest()
headers = {"Content-Type": "application/json", "X-APP-ID": app_id, "X-TIMESTAMP": str(timestamp), "X-Signature": sign}

resp = requests.post("https://api-ai.vivo.com.cn/v1/chat/completions", data=body, headers=headers)
print(resp.status_code, resp.text[:500])
```

验证项目：
- [ ] HTTP 200 响应
- [ ] 响应结构是否与 `choices[0].message.content` 兼容
- [ ] 是否支持 system prompt
- [ ] 是否支持 JSON mode 或 JSON output

### 4.2 E2E 验证

启动后端并执行：

```bash
export EXTERNAL_AI_ENABLED=true
export OCR_PROVIDER=vivo_general_ocr
export LLM_PROVIDER=vivo_bluelm
export VIVO_APP_ID=your_id
export VIVO_APP_KEY=your_key
cd demo-app/backend && uvicorn app:app
```

然后执行：

```bash
curl -X POST http://localhost:8000/api/v3/demo/evidence-search \
  -d '{"case_id": "demo-evidence-query-appetite-001", "question": "病人最近的材料中是否提到食欲不振？", "trigger_type": "question", "top_k": 5}' \
  -H 'Content-Type: application/json'
```

验证：
- [ ] 返回结果包含 items
- [ ] item 有 `segment_id`、`relevance_level`、`source_excerpt`
- [ ] `llm_mode` 为 `"vivo_bluelm"`
- [ ] 无结果时返回安全文案

## 5. 踩坑记录

| 问题 | 发现日期 | 解决方案 |
|------|---------|---------|
| (待填写) | | |
| (待填写) | | |

## 6. 验证结论

- OCR API: [ ] 成功接入 bbox / [ ] 成功接入纯文本 / [ ] 使用 fallback
- BlueLM LLM: [ ] 成功接入 / [ ] 无法使用 / [ ] 使用 mock fallback
- 最后验证日期：_________________
