# vivo AI 平台 API 接入验证报告

> 最后更新：2026-05-25
> 验证依据：用户已提供 v0.9.1 官方文档正文，确认字段已核实。

## 1. 目标

验证 `providers/vivo_general_ocr.py` 与 `providers/vivo_bluelm_evidence.py` 的适配器
是否能够正确连接 vivo AI 平台 API，并将返回结果映射为统一的 `OCRResult` 与 `LLMGroundedResult`。

## 2. 前置条件

- [x] 已从 [vivo AIGC 创新赛平台](https://aigc.vivo.com.cn/) 申请到 APP_ID 与 APP_KEY。
- [x] 已确认使用的 API 端点（已核实）：
  - OCR: `http://api-ai.vivo.com.cn/ocr/general_recognition`
  - Chat Completions: `https://api-ai.vivo.com.cn/v1/chat/completions`
- [ ] 已进行真实凭证 smoke test（未执行，因本地无有效凭证）

## 3. OCR API 核验结论

| 项目 | 已核实值 | 实现状态 |
| --- | --- | --- |
| 服务名称 | 通用 OCR | ✅ Provider: `VivoGeneralOCRProvider` |
| 接口地址 | `http://api-ai.vivo.com.cn/ocr/general_recognition` | ✅ 可配置，默认 HTTP |
| 请求方式 | `POST` | ✅ |
| Content-Type | `application/x-www-form-urlencoded` | ✅ |
| 鉴权 | `Authorization: Bearer AppKey` | ✅ |
| Query | `requestId=<uuid>`（必须） | ✅ |
| Body: `image` | base64，支持 jpg/png/bmp | ✅ |
| Body: `pos` | 0/1/2；本项目固定 `pos=2` | ✅ |
| Body: `businessid` | `"aigc"` + AppId | ✅ 含 env override |
| Body: `sessid` | 可选 UUID | ✅ |
| 返回：`error_code` | 0=成功，1=OCR失败，2=图像错误 | ✅ |
| 返回：`result.OCR[].words` | 文字 | ✅ |
| 返回：`result.OCR[].location` | 四点坐标（top_left/top_right/down_left/down_right） | ✅ 转换为 polygon & bbox |
| 返回：`angle` | 0/90/180/270 | ✅ 保存 |
| OCR 置信度 | ❌ **官方文档未列出** | ✅ live OCR confidence=null |
| 安全限制 | 官方文档为 HTTP | ⚠️ 仅允许 synthetic demo 调用 |

### 3.1 HTTPS 可用性

未测试。默认配置保持 `VIVO_OCR_BASE_URL=http://api-ai.vivo.com.cn`，用户可手动改为 HTTPS 测试。

### 3.2 坐标模式

`pos=2` 返回相对坐标（非归一化 0-1），provider 保留 `coordinate_mode="relative"`。
前端 `EvidenceCanvas` 需将相对坐标按图片展示尺寸映射。

## 4. LLM API 核验结论

| 项目 | 已核实值 | 实现状态 |
| --- | --- | --- |
| 接口地址 | `https://api-ai.vivo.com.cn/v1/chat/completions` | ✅ Provider: `VivoBlueLMEvidenceProvider`（mode=vivo_chat_completions）|
| 协议 | OpenAI-compatible Chat Completions | ✅ |
| 鉴权 | `Authorization: Bearer AppKey` | ✅ |
| Query 参数 | 表格写 `requestId`，示例用 `request_id` | ✅ 默认 `request_id`，兼容重试 `requestId` |
| 可用模型 | `Volc-DeepSeek-V3.2` / `Doubao-Seed-2.0-mini/lite/pro` / `qwen3.5-plus` | ✅ env 配置 |
| `stream` | true/false | ✅ 固定 false |
| `max_tokens` | 可选，默认 4096 | ✅ 设为 1024 |
| `reasoning_effort` | minimal/low/medium/high | ✅ DeepSeek 模型使用 |
| `enable_thinking` | 可选 | ✅ qwen 模型使用 |
| Function Calling | 文档支持，但本项目不使用 | ✅ 明确不引入 |

### 4.1 request id 参数兼容

默认使用 `request_id`（文档 Python/requests 示例用）。若返回 1001 错误，仅重试一次用 `requestId`。最终成功字段需在实际 smoke test 中确定。

### 4.2 当前状态

未进行真实凭证 smoke test（因本地无有效 API 凭证）。所有 API 行为验证通过 mock 单元测试完成。

## 5. 踩坑记录

| 问题 | 发现日期 | 解决方案 |
| --- | --- | --- |
| v0.8 `validate_evidence` 强制 confidence 在 0-1 之间，但 vivo 官方无此字段 | 2026-05-25 | ✅ 已修：`confidence=None` 允许通过 |
| `vivo_auth.py` 旧版使用 HMAC-SHA256 签名（X-APP-ID + X-Signature） | 2026-05-25 | ✅ 已修：改为 Bearer 模式 |
| `provider_registry.py` 中 LLM mode 写为 `vivo_bluelm` | 2026-05-25 | ✅ 已修：改为 `vivo_chat_completions` |
| `.gitignore` 缺少 vivo raw response 的忽略规则 | 2026-05-25 | ✅ 已修 |
| `app.py` smoke-test 端点在重构后遗留了 `build_vivo_sign_headers` 导入 | 2026-05-25 | ✅ 已更新为 `build_vivo_bearer_headers` |

## 6. 验证结论

- OCR API: [ ] 成功接入 bbox / [x] 适配器就绪，等待真实凭证 / [x] 透明 fallback 到 sidecar
- LLM API: [ ] 成功接入 / [x] 适配器就绪，等待真实凭证 / [x] 透明 fallback 到本地检索
- 最后验证日期：2026-05-25（仅单元测试，未进行真实 API 调用）
