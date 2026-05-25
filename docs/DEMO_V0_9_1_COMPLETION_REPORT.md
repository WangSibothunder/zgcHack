# 转诊迹 v0.9.1-Resolved 完成报告

> 完成日期：2026-05-25
> 执行依据：`docs/PRD_V0_9_1_VIVO_API_RESOLVED_PATCH.md`

## 一、版本概要

本版本在 v0.8（合成上传/OCR/证据核验）和 v0.9（证据联查）基础上，完成了以下关键修订：

1. **vivo API 接口字段按已核实文档补齐**：将此前"等待官方页面核实"的 placeholder 替换为已确认字段
2. **OCR provider 重构**：从 HMAC-SHA256 签名改为 Bearer 鉴权，与已核实 PRD 保持一致
3. **LLM provider 重构**：mode 从 `vivo_bluelm` 改为 `vivo_chat_completions`，使用 OpenAI-compatible 协议
4. **验证层修复**：`validate_evidence` 中 `confidence=None` 允许通过（vivo 官方不提供该字段）
5. **鉴权统一**：移除旧版 `build_vivo_sign_headers`，统一使用 `build_vivo_bearer_headers` 和 `build_vivo_ocr_headers`
6. **文档同步**：更新 `.env.example`、`.gitignore`、`docs/VIVO_API_VERIFICATION.md`

## 二、vivo OCR 接入结果

| 项目 | 结论 |
| --- | --- |
| adapter 是否完成 | ✅ `VivoGeneralOCRProvider` 已实现，含 pos=2 坐标解析 |
| 是否用真实凭证对合成样例调用 | ❌ 未运行（本地无可用的 API 凭证） |
| 使用的 endpoint scheme | 默认 HTTP (`VIVO_OCR_BASE_URL=http://api-ai.vivo.com.cn`) |
| pos 参数 | 2 |
| 是否返回可渲染位置 | ✅ pos=2 模式支持四点坐标 → polygon/bbox 转换 |
| 是否提供置信度 | ❌ 官方文档未发现；live OCR 的 `confidence=null` |
| fallback 是否可运行 | ✅ 透明降级到 `SyntheticOCRProvider`（sidecar / 硬编码 fallback） |

## 三、vivo LLM 接入结果

| 项目 | 结论 |
| --- | --- |
| adapter 是否完成 | ✅ `VivoBlueLMEvidenceProvider` 已实现，OpenAI-compatible |
| 是否用真实凭证对合成候选片段调用 | ❌ 未运行（本地无可用的 API 凭证） |
| 实际成功模型 | 未运行，默认配置 `qwen3.5-plus`，可通过 env 切换 |
| request id query 字段实际成功值 | 未运行；默认 `request_id`，兼容重试 `requestId` |
| 是否成功解析 grounded JSON | 仅单元测试验证，未真实 API 调用 |
| API 不可用时本地检索是否可运行 | ✅ `LocalEvidenceLLMProvider` 始终可用 |

## 四、数据安全检查

| 项目 | 结论 |
| --- | --- |
| 外部调用材料是否全部 synthetic | ✅ provider 始终断言 `synthetic=true` |
| 是否存在真实病历 | ✅ 无：所有 fixture 为虚构合成数据 |
| `.env` 是否未追踪 | ✅ `.gitignore` 覆盖 `.env`、`.env.*` 排除 `.env.example` |
| AppKey 是否未进入前端 bundle / logs / git | ✅ 仅后端读取，`redact_sensitive_headers` 脱敏日志 |
| runtime/raw response 是否未追踪 | ✅ `.gitignore` 新增 `*vivo_api_raw_*`、`*external_api_debug*` |

## 五、关键修复清单

| 问题 | 修复 |
| --- | --- |
| v0.8 `validate_evidence` 拒绝 `confidence=None` | ✅ 改为仅在有值时校验 0~1 范围 |
| `vivo_auth.py` 使用 HMAC-SHA256 签名 | ✅ 改为 Bearer 鉴权 |
| LLM provider mode 写为 `vivo_bluelm` | ✅ 改为 `vivo_chat_completions` |
| `app.py` smoke-test 导入旧函数 | ✅ 更新为 `build_vivo_bearer_headers` |
| 缺少 raw response 忽略规则 | ✅ 加入 `.gitignore` |
| `.env.example` 与已核实 PRD 字段不匹配 | ✅ 完全重写为 v0.9.1-Resolved 版 |

## 六、测试结果

- **后端 pytest**: 35/35 passed
- **测试覆盖**: auth → OCR → LLM → provider status → validate_llm_items → smoke-test
- **前端测试**: 未修改，需要单独执行 `npm test`

## 七、遗留问题

1. **真实 API smoke test 未运行**：需要本地填写 `.env` 中的 `VIVO_APP_ID` 和 `VIVO_APP_KEY`
2. **OCR HTTPS 可用性未验证**：默认 HTTP；手动设 `VIVO_OCR_BASE_URL=https://...` 后需测试
3. **request id 参数兼容**：代码支持 `request_id` ↔ `requestId` 兼容重试，但未验证实际 API 行为
4. **坐标尺度确认**：`pos=2` 返回相对坐标，但未验证实际基准值（[0,1] 或百分比或固定基准）

## 八、公开仓库状态

- 仓库：`WangSibothunder/zgcHack` (public)
- 当前分支：`main`
- 与上游一致性：origin/main 一致
- 本地 v0.9.1 修订：尚未 commit/push
