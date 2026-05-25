# 转诊迹 v0.9 + v0.9.1 实施清单

## 阶段 1：基础结构（v0.9 已有部分）
- [x] 后端 evidence_search.py（DocumentSegment、关键词+同义词召回、LLM rerank 整合）
- [x] external_ai.py（Provider 抽象、MockEvidenceLLMProvider、ExternalOCRApiProvider）
- [x] evidence_search_system.txt（系统提示词模板）
- [x] 前端 EvidenceSearchPanel、搜索结果卡片、关联记录区域
- [x] demo-evidence-query-appetite-001.json（食欲联查合成病例）
- [x] API: /api/v3/demo/cases/{case_id}/segments/rebuild
- [x] API: /api/v3/demo/evidence-search
- [x] API: /api/v3/demo/cases/{case_id}/evidence-search-history
- [x] 后端测试覆盖（重建、召回、排除、无结果、历史记录、外部 OCR 映射）

## 阶段 2：v0.9.1 Provider 目录与 vivo API 适配器
- [x] 创建 providers/base.py - OCRBlock、OCRResult 数据模型
- [x] 创建 providers/vivo_auth.py - vivo 签名实现
- [x] 创建 providers/vivo_general_ocr.py - VivoGeneralOCRProvider
- [x] 创建 providers/vivo_bluelm_evidence.py - VivoBlueLMEvidenceProvider
- [x] 创建 providers/synthetic_ocr.py - 将旧 fallback 迁移到 provider 包
- [x] 创建 providers/local_evidence_llm.py - 将 mock provider 迁移到 provider 包
- [x] 注册 provider_registry.py

## 阶段 3：环境变量与安全
- [x] 更新 .env.example（vivo APP_ID/APP_KEY、OCR/LLM host/path/model 和开关）
- [x] 更新 .gitignore（已包含 runtime、环境变量、数据库）

## 阶段 4：API 新增端点
- [x] 新增 GET /api/v3/demo/providers/status
- [x] 新增 POST /api/v3/demo/providers/vivo/smoke-test

## 阶段 5：文档
- [x] 创建 docs/VIVO_API_VERIFICATION.md
- [x] 创建 docs/API_CONTRACT_V3.md
- [x] 创建 docs/DEMO_V0_9_1_COMPLETION_REPORT.md
- [x] 更新 README.md（v0.9 证据联查演示说明 + Provider 状态查看命令）

## 阶段 6：测试
- [x] 创建 tests/fixtures/vivo/ocr_success_with_bbox.json
- [x] 创建 tests/fixtures/vivo/ocr_success_text_only.json
- [x] 创建 tests/fixtures/vivo/llm_grounded_success.json
- [x] 创建 tests/fixtures/vivo/llm_invalid_segment.json
- [x] 创建 tests/test_vivo_providers.py
- [x] 运行全套测试：36 passed ✓

## 阶段 7：前端 Provider 状态展示
- [ ] 前端 provider 状态标识（vivo OCR / 预置合成 OCR / BlueLM / 本地检索）

## 阶段 8：最终安全检查
- [x] 检查无 .env、key、runtime 文件被追踪
- [x] 检查无真实患者数据
- [x] 确认仓库保持 public
