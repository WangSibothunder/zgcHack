# 历刻（zgcHack）｜转院病历重建系统 Demo

本仓库是一个 public synthetic demo，用于展示转院患者外院材料的时间轴整理、字段核验和证据回溯。它不包含真实病历，全部病例、OCR 内容、影像/检验字段和材料图片均为**合成演示数据**，不得被用于临床判断。

## Demo 目标

面向“患者从外院转入新医院”的接诊前材料整理场景，实现以下闭环：

1. 用户选择一位合成转院患者或模拟上传材料；
2. 后端返回按日期聚合的时间轴节点；
3. 前端按“一日一节点”展示原图缩略图、概要、异常提示；
4. 医生可点击节点查看 OCR、结构化字段与证据定位；
5. 页面明确显示“合成演示数据，仅用于材料整理演示，不构成诊断或治疗建议”。

## 本包包含什么

- `AGENTS.md`：应放在仓库根目录、会被 Codex 自动读取的项目指令文件。
- `agent.md`：便于人工阅读/复制的同内容说明文件；实际运行时以 `AGENTS.md` 为准。
- `.codex/skills/*/SKILL.md`：六个可复用专项工作流。
- `CODEX_TONIGHT_PROMPT.md`：今晚直接发送给 Codex 的完成型任务指令。
- `docs/`：范围、API、数据安全、验收和 GitHub 发布说明。
- `demo-data/`：三位虚构转院患者、节点材料、证据链和 SVG “原始材料”占位图。
- `demo-app/backend/`：可独立运行的 FastAPI mock API，读取 `demo-data/` fixtures。
- `demo-app/frontend/`：Vite + React + TypeScript 前端，通过 HTTP API 加载病例、时间轴和材料证据。
- `reference/`：用户现有视觉原型与需求文档的只读参考副本。

## 本地运行

先启动后端。

终端 A：

```bash
cd demo-app/backend
python3 -m venv .venv
source .venv/bin/activate        # Windows 使用 .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

再启动前端。

终端 B：

```bash
cd demo-app/frontend
npm install
npm run dev -- --port 5173
```

浏览器打开 `http://127.0.0.1:5173`。前端会访问 `http://127.0.0.1:8000` 的 mock API。

## 测试与验收命令

后端：

```bash
cd demo-app/backend
source .venv/bin/activate
pytest -q
```

前端：

```bash
cd demo-app/frontend
npm run lint
npm run typecheck
npm test
npm run build
npm run smoke
```

`npm run smoke` 会使用本机 Google Chrome 跑 Playwright 浏览器流程；若本机没有 Chrome，可先安装浏览器或调整 `demo-app/frontend/playwright.config.ts`。

## 演示步骤

1. 打开 `http://127.0.0.1:5173`，确认顶部显示合成数据与非诊断提示。
2. 默认进入心内科病例，横向浏览 6 个按日期排序的时间轴节点。
3. 点击节点查看右侧详情、结构化字段、OCR 片段、材料预览和材料完整性提示。
4. 点击证据项打开合成原始材料，查看定位文字、OCR 置信度和核验状态。
5. 使用“只看异常”“与转院原因相关”“材料类型”筛选。
6. 切换到神经内科病例，查看低置信度字段提示。
7. 点击“模拟上传”，确认任务完成后回到生成的合成病例时间轴。

## v0.8 采集演示

1. 切换到“采集新材料”。
2. 上传 `demo-data/capture-samples/degraded/cardiac_lab_blurred.png`，页面会提示“需重拍”。
3. 上传 `demo-data/capture-samples/originals/cardiac_lab_clear.png`，系统会接收真实图片字节并进入质量检测、OCR fallback、字段抽取和时间轴生成。
4. 回到“医生时间轴”，打开“现场合成材料处理结果”节点。
5. 点击证据项，原图上会显示 bbox 高亮框。
6. 点击“确认正确”或“标记需复核”。
7. 切换到“接诊前摘要”，查看现场材料数量和核验计数。

当前 OCR 模式为 `deterministic_synthetic`，页面显示“预置合成 OCR 演示回放”。这是一种可复现 fallback，不伪称真实 OCR 引擎处理。

## v0.9 证据联查演示

1. 进入医生时间轴，在顶部"证据联查"搜索框中输入"病人最近的材料中是否提到食欲不振？"
2. 系统返回关联的材料记录，包含日期、文档类型、原文片段和"查看原图证据"按钮。
3. 点击"查看原图证据"，时间轴定位到对应节点，原图上高亮显示相关文字。
4. 选中节点详情页中的某段 OCR 文本，选择"联查相关证据"，文本下方展示其他日期的关联材料。
5. 无结果时系统显示"当前未检索到明确相关记载，不代表患者不存在该情况"的安全文案。

### Provider 状态查看

```bash
# 查看当前 OCR 与 LLM provider 配置
curl http://localhost:8000/api/v3/demo/providers/status

# 测试 vivo 鉴权配置（需先设置 VIVO_APP_ID / VIVO_APP_KEY）
curl -X POST http://localhost:8000/api/v3/demo/providers/vivo/smoke-test
```

启用外部 API（需有效 vivo 平台 APP_ID/APP_KEY）：

```bash
cd demo-app/backend
cp ../../.env.example .env
# 编辑 .env，设置 EXTERNAL_AI_ENABLED=true 并填写 VIVO_APP_ID/VIVO_APP_KEY
```

## 三分钟路演脚本

1. 选择“周启明（A01）｜心内科”，说明这是合成转院材料整理演示。
2. 先看顶部“重点核验线索”：系统把 ST-T、CK-MB、肌钙蛋白等原文标记字段聚合出来。
3. 沿时间轴从 2024-03-12 最早胸部不适看到 2025-01-15 转院前复诊，说明一日一节点和证据链。
4. 点击“肌钙蛋白 I”或“ST-T 改变”，打开原图证据 modal，展示 OCR、bbox 和医生核验按钮。
5. 在证据联查中搜索“这个患者最早什么时候出现胸部不适？”，展示同义词召回和历史材料定位。
6. 切到“只看异常”或“与转院原因相关”，展示医生如何快速收敛到关键材料。
7. 切到“采集新材料”，上传清晰合成化验单，系统把新增材料追加到当前病例时间轴。
8. 切到“接诊前摘要”，展示转院相关节点、待核验字段数量和材料完整性提示。
9. 结尾说明：历刻只做材料整理、证据定位和待核验提醒，不生成诊断或治疗建议。

## 重要边界

- GitHub 仓库 `WangSibothunder/zgcHack` 保持公开，仅用于展示合成材料流程。
- Demo 阶段只能使用合成数据，不接入真实患者资料。
- 不提交 API Key、`.env`、token、cookie、runtime 上传内容、OCR 缓存、数据库运行文件或日志。
- 系统只承担材料整理、时间排序、字段提取与证据追溯，不生成诊断结论或治疗方案。
- 未来真实材料必须进入独立合规环境，并先完成授权、脱敏、访问控制、存储加密、数据保留与删除策略、日志审计和合规评审。

