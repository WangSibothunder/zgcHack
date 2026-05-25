# 转诊迹 v0.8 Completion Report

## Verification Date

2026-05-25, Asia/Shanghai.

## Implemented

- 品牌升级：转诊迹｜转院病历证据时间轴。
- 医生时间轴、采集新材料、接诊前摘要三 Tab。
- `POST /api/v2/demo/ingestions` 接收合成图片字节。
- 合成图片质量检测：清晰、模糊需重拍、反光 warning。
- deterministic OCR fallback with sidecar bbox，不伪称真实 OCR。
- 上传清晰样例后生成/插入现场合成材料节点。
- 证据弹窗支持 bbox 高亮。
- 医生 review：确认正确、需复核、修改字段，写入 runtime。
- 接诊前摘要：节点、现场材料、核验计数、转院相关节点、材料完整性提示。
- public 仓库安全策略和 `.gitignore` runtime 保护。

## Commands And Results

```bash
cd demo-app/backend
.venv/bin/python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
.venv/bin/python -m pytest -q
# 13 passed in 0.26s
```

```bash
cd demo-app/frontend
npm run lint
npm run typecheck
npm test
npm run build
# lint passed; typecheck passed; Vitest 5 passed; Vite build passed
```

```bash
cd demo-app/frontend
npm run smoke
# Playwright 3 passed in 10.3s
```

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok","service":"zhuanzhenji-demo-api","mode":"synthetic-demo"}
```

## Public Repo Safety Check

Expected final command before push:

```bash
git status --short
git ls-files | grep -Ei 'runtime|\.env|sqlite|\.db|token|secret' || true
```

`.gitignore` now covers `runtime/`, `demo-app/backend/runtime/`, `*.sqlite`, `*.sqlite3`, `*.db`, `*.log`, uploads and real-data folders.

## Demo Script

1. 打开“转诊迹”，说明这是合成材料流程。
2. 在医生时间轴展示既有合成病例、筛选和证据弹窗。
3. 进入“采集新材料”，上传 `cardiac_lab_blurred.png` 展示重拍提示。
4. 上传 `cardiac_lab_clear.png`，展示质量通过、OCR fallback、字段抽取和时间轴节点生成。
5. 打开新增节点证据，查看原图 bbox 高亮。
6. 点击“确认正确”。
7. 进入接诊前摘要，展示已确认计数和材料完整性提示。

## Boundary

本版本仍仅使用合成演示材料。系统只整理材料、字段和证据，不生成诊断或治疗建议。真实材料必须在独立合规环境中验证。
