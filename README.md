# zgcHack：转院病历时间轴 Demo

本仓库是一个可本地演示的前后端分离 Demo，用于转院患者外院材料的时间轴整理、字段核验和证据回溯。它不包含真实病历，全部病例、OCR 内容、影像/检验字段和材料图片均为**合成演示数据**，不得被用于临床判断。

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

## 重要边界

- Demo 阶段只能使用合成数据，不接入真实患者资料。
- 系统只承担材料整理、时间排序、字段提取与证据追溯，不生成诊断结论或治疗方案。
- 即便未来接入真实材料，也必须先完成隐私、访问控制、数据保留策略与合规评审。
