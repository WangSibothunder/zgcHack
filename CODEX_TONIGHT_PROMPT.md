# 发送给 Codex 的今晚交付指令：zgcHack Demo 必须闭环

你现在负责把本仓库推进到可以现场演示的 Demo 完成状态。先读取仓库根目录 `AGENTS.md`，并按需调用：

- `$product-scope`
- `$synthetic-medical-data`
- `$backend-mock-api`
- `$frontend-timeline`
- `$evidence-traceability`
- `$demo-delivery-loop`

## 任务背景

产品聚焦转院场景：患者携带外院纸质病历或截图进入新医院，医生需要快速了解既往诊疗过程。现有视觉原型的核心交互是横向时间轴：一个时间点一个节点，节点上方显示原始材料缩略图，下方显示结构化概要；点击节点查看 OCR、关键字段、证据来源和材料预览。

Demo 阶段只能使用 `demo-data/` 中的合成数据，绝不处理或提交真实病例。系统只做材料整理与证据回溯，不给出诊断或治疗建议。

## 第一原则

不要停留在计划、分析或“后续可以做”。你需要在当前仓库中持续实现、运行、验证、修复，再验证，直到 `docs/DEMO_ACCEPTANCE.md` 的必做项全部通过。遇到构建错误、接口错配或 UI 问题，直接诊断并修复；每轮改动后立即运行相关检查。

唯一可能在本地功能完成后阻止最后上传的外部因素，是 GitHub 账号认证/授权不可用。即便发生这种情况，也必须先把本地 Demo 全部做完并输出完整验收证据。

## 执行顺序

### 1. 盘点仓库并确定最小改动方案

- 查看当前文件树、依赖、已有前端框架、启动命令和 Git 状态。
- 将 `reference/transfer_medical_timeline_mockup.html` 视为视觉基线。
- 如果已有前端工程，直接在其上集成；如果只有静态 HTML，构建最小可维护的前端工程。
- 若没有后端，创建独立后端服务；优先读取 `docs/API_CONTRACT.md`。

先输出你发现的现状与本轮将实现的最小路径，然后立刻执行，不等待确认。

### 2. 完成数据与后端闭环

- 使用 `demo-data/cases/*.json` 作为唯一病例来源。
- 实现健康检查、病例列表、时间轴、材料详情、模拟上传、任务状态接口。
- 校验 synthetic 标识、时间顺序、引用完整性与证据字段。
- 暴露合成材料 SVG 静态资源。
- 加入 backend tests 并运行通过。

### 3. 完成前端闭环

- 将原型中的硬编码 records 替换为 API 加载的数据模型。
- 保留或复现：顶部转院摘要、横向时间轴、节点概要、右侧详情、证据弹窗。
- 实现：三个病例切换、异常/材料类型/转院相关筛选、模拟上传流程、材料缺失提醒。
- 实现：loading、empty、API error retry、低置信度标记。
- 页面显著展示：`合成演示数据，仅用于材料整理演示，不构成诊断或治疗建议。`
- 完成响应式与基础可访问交互。

### 4. 验收、修复、记录

- 运行 lint/typecheck/build/test（以仓库实际栈为准）。
- 本地同时启动前后端，完整走一遍主流程。
- 用真实执行结果填写 `docs/DEMO_COMPLETION_REPORT.md`。
- 对照 `docs/DEMO_ACCEPTANCE.md`，凡是未通过项立刻继续实现与修复，不能以 TODO 收尾。
- 检查没有 token、`.env`、真实病例或个人信息被跟踪。

### 5. 完成后推送到 GitHub public 仓库

全部验收完成后，推送到现有公开 GitHub 仓库 `WangSibothunder/zgcHack`。该仓库用于黑客松作品展示，保持 public；前提是完成 public 安全扫描，确认没有真实病历、密钥、`.env`、runtime 上传文件、数据库运行文件或日志。优先使用 GitHub CLI：

```bash
gh auth status
git status --short
git add .
git commit -m "feat: deliver synthetic transfer timeline demo"
git branch -M main
git remote add origin git@github.com:WangSibothunder/zgcHack.git  # 若尚未设置 origin
git push -u origin main
```

若仓库已经初始化或已有提交历史，请保留历史并只提交当前必要变更。若 `gh auth status` 表明未授权或缺少 GitHub CLI，不得声称推送成功：完成本地所有验收后，明确报告需要我执行的唯一授权步骤和待重试的推送命令。

## 最终输出格式

只有在本地 Demo 验收闭环完成后，才能给最终汇报。最终汇报必须包含：

1. 已实现功能列表；
2. 实际目录/架构；
3. 实际运行和测试命令及结果；
4. Demo 演示步骤；
5. synthetic-only 与非诊断边界确认；
6. GitHub public 仓库 `WangSibothunder/zgcHack` push 的实际结果，或唯一剩余的认证/工具阻塞。
