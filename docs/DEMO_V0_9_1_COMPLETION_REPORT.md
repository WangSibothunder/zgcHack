# 转诊迹 v0.9.1 完成报告：Provider 目录重构 + vivo API 适配

> 完成日期：2026-05-25  
> 仓库：`WangSibothunder/zgcHack`（公开）

## 1. 变更摘要

根据 `PRD_V0_9_EVIDENCE_LINKED_SEARCH.md`（第 8、14 节）与 `PRD_V0_9_1_VIVO_API_INTEGRATION.md`：

### 已完成

- ✅ **Provider 目录重构**：从 `services/external_ai.py` 中提取 Provider 协议，迁移到独立 `providers/` 包
- ✅ **基础数据模型**：`OCRBlock`、`OCRResult`、`LLMGroundedItem`、`LLMGroundedResult`
- ✅ **vivo 鉴权模块**：`providers/vivo_auth.py`——HMAC-SHA256 签名 + header 脱敏
- ✅ **vivo OCR adapter**：`providers/vivo_general_ocr.py`——polygon → bbox 转换
- ✅ **vivo BlueLM adapter**：`providers/vivo_bluelm_evidence.py`——grounded rerank + segment_id 校验
- ✅ **合成 OCR provider**：`providers/synthetic_ocr.py`——从 sidecar 读取的 fallback
- ✅ **本地证据 LLM provider**：`providers/local_evidence_llm.py`——关键词匹配 mock
- ✅ **Provider 注册中心**：`providers/provider_registry.py`——按环境变量返回正确实例
- ✅ **vivo BlueLM 系统提示词**：`prompts/vivo_evidence_linked_search_system.txt`
- ✅ **环境变量更新**：`.env.example` 新增 vivo 配置占位符
- ✅ **新增 API 端点**：
  - `GET /api/v3/demo/providers/status`
  - `POST /api/v3/demo/providers/vivo/smoke-test`
- ✅ **测试覆盖**：`tests/test_vivo_providers.py`（18 个测试）+ 4 个 vivo 测试 fixture JSON
- ✅ **验证文档**：`docs/VIVO_API_VERIFICATION.md`
- ✅ **API 合同文档**：`docs/API_CONTRACT_V3.md`

### 未变更

- 证据联查业务层（`services/evidence_search.py`）不改动
- 前端层不改动（provider 状态标识未来版本添加）
- 所有现有测试仍然通过
- `external_ai.py` 保留向后兼容

## 2. 重要设计决策

| 决策 | 理由 |
|------|------|
| host/path/model 从 `.env` 读取 | 允许跟随官方文档调整，不写死 |
| BlueLM adapter 兼容 OpenAI-compatible 响应 | 多数 LLM API 遵循此模式 |
| vivo auth 使用 `X-APP-ID`、`X-Signature`、`X-TIMESTAMP` | 基于 vivo AIGC 创新赛已知鉴权模式 |
| polygon 自动转换 bbox | 统一高亮坐标系 |
| segment_id 校验 | 防止 LLM 编造来源 |
| 未配置时返回空列表/错误信息而非异常 | 不阻塞正常演示流程 |

## 3. 外部 API 接入状态

### 3.1 OCR API

**当前 provider：** `deterministic_synthetic`（预置合成 OCR 回放）

真实 vivo OCR API 接入**待用户提供有效 APP_ID/APP_KEY** 后验证。

一旦验证通过，设置：
```
EXTERNAL_AI_ENABLED=true
OCR_PROVIDER=vivo_general_ocr
```

然后在 `VIVO_API_VERIFICATION.md` 中填写结果。

### 3.2 LLM API

**当前 provider：** `mock`（本地证据检索）

真实 vivo BlueLM API 接入同样**待用户提供有效 APP_ID/APP_KEY** 后验证。

一旦验证通过，设置：
```
EXTERNAL_AI_ENABLED=true  
LLM_PROVIDER=vivo_bluelm
```

## 4. 测试结果

```
tests/test_api.py          — 13 个测试全部通过
tests/test_vivo_providers.py — 18 个测试全部通过
```

## 5. 公开仓库安全检查

- [x] `.env.example` 只包含占位符
- [x] `.env` 已被 `.gitignore`
- [x] `.env.*` 已被 `.gitignore`（除 `.env.example`）
- [x] `runtime/` 已被 `.gitignore`
- [x] `*.db`、`*.sqlite`、`*.sqlite3` 已被 `.gitignore`
- [x] 无真实患者数据
- [x] 仓库保持 public
- [x] 无 API key 硬编码

## 6. 后续使用指引

1. 从 vivo AIGC 创新赛平台申请 APP_ID/APP_KEY
2. 复制 `.env.example` 为 `.env` 并填写
3. 参考 `docs/VIVO_API_VERIFICATION.md` 验证 API
4. 如果 API host/path/model 与实际分配的不同，修改 `.env` 对应字段
5. 如果 JSON 响应结构与 adapter 预期不同，修改对应 provider 的解析方法
