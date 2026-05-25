# 转诊迹 / zgcHack：云端现状审查与新 Codex 修复指导（v0.9.1）

> **检查对象**：公开仓库 `WangSibothunder/zgcHack` 的 GitHub `main` 分支。  
> **检查时点**：2026-05-25。  
> **重要说明**：本报告仅反映已 push 到云端的版本；上一位 Codex 若在本地或未提交分支中已有 v0.8/v0.9 改动，本报告看不到这些工作。新 Codex 开始时必须先检查 `git status`、`git log --all` 与 `git diff`，不得用远端旧版本覆盖本地进度。  
> **本报告用途**：与 `docs/PRD_V0_9_1_VIVO_API_RESOLVED_PATCH.md` 以及新的接管 Prompt 一起提供给 Codex，帮助其快速定位当前远端基础与需要优先修复的冲突。

---

## 1. 云端已确认具备的基础

当前公开 `main` 可确认有以下基础能力：

| 项目 | 云端状态 | 判断 |
| --- | --- | --- |
| 仓库可见性 | Public | 与当前展示策略一致，无需改 private |
| 提交历史 | GitHub 页面目前显示 2 commits | v0.8/v0.9 功能尚未在远端可见，或仍未 push |
| 工程栈 | `demo-app/backend` FastAPI；`demo-app/frontend` Vite + React + TypeScript | 可继续增量开发，不需重建项目 |
| fixtures | `demo-data/` 存在三类合成病例 | 可保留作为离线演示 fallback |
| 指令文件 | 根目录有 `AGENTS.md` 与 `agent.md` | 已写入“转诊迹”和 public synthetic-only 策略 |
| Skills | `.codex/skills/` 下有 6 个专项 skill | 可复用，但部分内容与 v0.9.1 冲突，需要更新 |
| 安全忽略 | `.gitignore` 已忽略 `.env`、runtime、数据库、日志、real-data 等 | 基础较好，仍需增加 raw API debug 防护 |
| 基础验收记录 | `docs/DEMO_COMPLETION_REPORT.md` 记录 v1 fixture Demo 测试通过 | 这是旧 mock Demo 验收，不等价于新 API/证据联查完成 |

---

## 2. 最关键判断：云端仍是 v1 Mock Demo，不是当前目标版本

### 2.1 README 仍描述旧产品阶段

远端 README 标题仍是：

```text
zgcHack：转院病历时间轴 Demo
```

并说明：

```text
后端为 FastAPI mock API，读取 demo-data fixtures；
演示步骤包含“模拟上传”；
页面通过 mock API 加载病例。
```

这说明云端 README 还没有落实：

- “转诊迹”正式品牌标题；
- v0.8 真实合成图片上传/采集；
- vivo OCR 增强模式；
- v0.9 证据联查；
- v0.9.1 provider 与 fallback 透明标识。

### 2.2 后端仍只有 v1 fixture API

远端 `demo-app/backend/app.py` 可直接确认：

- `UploadRequest` 只包含 `fixture_case_id` 和 `file_names`；
- `/api/v1/demo/uploads` 立即返回固定 fixture case 的 completed job；
- `/api/v1/demo/jobs/{job_id}` 同样只返回固定完成状态；
- 没有 multipart 图片字节接收；
- 没有 runtime 上传存储；
- 没有图像质量检测；
- 没有 OCR provider；
- 没有 vivo API；
- 没有 review persistence；
- 没有 DocumentSegment/index；
- 没有 evidence search/provider status/smoke test 接口。

因此，若新 Codex 所在工作区也与远端一致，需要从旧 v1 保持兼容地新增 v2/v3，而不是将 v1 当作已实现的新版本。

### 2.3 完成报告只覆盖旧 Mock 验收

远端完成报告明确写道：

```text
The upload flow accepts fixture case IDs and demo file names only;
it does not process real patient files or claim real OCR.
```

并报告的是 v1 mock flow 的 `pytest` / Vitest / Playwright 结果。该报告不证明以下新功能存在：

- 真正接收合成图片字节；
- OCR 与 bbox；
- vivo provider；
- 证据联查；
- 医生修改/确认审计；
- provider fallback 展示。

新 Codex 应保留旧报告作为历史记录，并新增 v0.9.1 completion report，不要覆盖历史事实写成“旧版本已经支持 OCR”。

---

## 3. 已发现的规则冲突：必须在编码前修正

## 3.1 `AGENTS.md` / `agent.md` 的 API 路径冲突

远端两个规则文件均写有类似约束：

```text
All API paths should be versioned below /api/v1/demo/.
```

这与目前需求冲突：

- v1 应保留为已有 fixture 浏览和兼容性 API；
- v2 应承载真实字节合成材料上传、处理任务、review、summary；
- v3 应承载证据联查、provider status 与 vivo synthetic smoke test。

### 修复指令

同步修改 `AGENTS.md` 与 `agent.md`：

```text
保留 `/api/v1/demo/` 的 fixture API 向后兼容；
新增 `/api/v2/demo/` 处理 ingestion/review/summary；
新增 `/api/v3/demo/` 处理 evidence-search/providers；
更新 API 文档、frontend adapters 与测试后方可变更 response shape。
```

## 3.2 `AGENTS.md` / `agent.md` 的 OCR confidence 冲突

远端规则要求 evidence 包含 OCR confidence。与此同时，已提供的 vivo OCR 文档返回文字、位置、角度和错误状态，但未列出 confidence 字段。

### 修复指令

修改规则为：

```text
- fixture/sidecar 数据可以显示明确标注为“预置演示置信度”的值；
- live vivo OCR 的 confidence 必须允许为 null；
- UI 必须显示“位置由 vivo OCR 返回；接口未提供识别置信度”；
- 禁止将 fixture 中的 0.91 等数值复用为 live API 输出。
```

## 3.3 `backend-mock-api` skill 明确禁止当前必需功能

远端 `.codex/skills/backend-mock-api/SKILL.md` 当前写有：

```text
Keep all application routes under /api/v1/demo/
Do not introduce a real patient upload pathway during Demo.
Do not connect to external health APIs.
```

其中“禁止真实患者上传”仍然正确；但“只允许 v1”“不连接外部 API”与当前 synthetic-only vivo Demo 冲突。

### 修复指令

不要删除该 skill 的离线 fallback 价值。将其改名或扩展表述为：

```text
- v1 mock API 必须保留，作为无需凭证的离线演示与测试基线；
- 允许新增 v2/v3，只接收带水印的 synthetic material；
- 允许本地配置 vivo OCR/LLM 对 synthetic material 做增强演示；
- 绝不允许真实患者数据或凭证进入 public 仓库。
```

同时新增更清楚的：

```text
.codex/skills/vivo-api-providers/SKILL.md
.codex/skills/evidence-linked-search/SKILL.md
```

## 3.4 `evidence-traceability` skill 要求 confidence 永不缺失

远端 `.codex/skills/evidence-traceability/SKILL.md` 当前写有：

```text
Ensure evidence payload never omits confidence or source locator.
Show source image, OCR excerpt, locator and confidence together.
```

### 修复指令

更新为：

```text
locator/bbox 是证据追溯必需字段；
confidence 仅在 provider 实际提供或 sidecar 明确预置时展示；
live vivo OCR 未提供 confidence 时，字段为 null 并展示能力说明；
不得为获得“完整 UI”而虚构置信度。
```

---

## 4. 代码级问题与修复优先级

## P0-1：保护上一 Codex 的本地工作

### 风险

云端只显示旧基线，但用户明确表示上一 Codex 正在执行新指导。新 Codex 若从远端版本直接强制覆盖，很可能丢失未 push 的 v0.8/v0.9 修改。

### 必做动作

```bash
git status --short --branch
git log --oneline --decorate --graph --all -20
git diff --stat
git stash list
find docs -maxdepth 1 -type f | sort
```

只有确认无有价值本地改动后，才能从远端基础继续实现。

---

## P0-2：将新 PRD 真正纳入仓库

### 观察

当前远端 `docs/` 列表没有出现：

```text
PRD_V0_8_ZHUANZHENJI.md
PRD_V0_9_EVIDENCE_LINKED_SEARCH.md
PRD_V0_9_1_VIVO_API_RESOLVED_PATCH.md
VIVO_API_VERIFICATION.md
API_CONTRACT_V2.md
API_CONTRACT_V3.md
PUBLIC_DATA_POLICY.md
```

### 修复

把用户提供的 v0.9.1 resolved patch 放到仓库的规范路径；若旧 Codex 已写入 v0.8/v0.9，则保留并统一命名；若不存在，可从任务上下文补写必要文档，至少保证最终实现有契约和验收依据。

---

## P0-3：品牌未完整更新

### 观察

`AGENTS.md` 已使用“转诊迹”，但 README、FastAPI title 和 health service 仍沿用 `zgcHack`/旧 Demo 名称；前端当前云端内容也应检查标题和浏览器 title 是否仍为旧名称。

### 修复

用户可见品牌统一为：

```text
转诊迹｜转院病历证据时间轴
把散落病历，连成可核验的转院时间轴。
```

仓库名称保留 `zgcHack`，作为技术仓库/比赛标识。

---

## P0-4：后端为单文件旧模型，无法支撑新链路

### 观察

远端 `app.py` 约 193 行，负责 fixtures 校验与所有 v1 路由。新链路将引入 ingestion、OCR provider、LLM provider、review store、segment index、evidence search 和 provider status。继续全部堆进 `app.py` 会极易造成回归和测试困难。

### 修复方向

保留 v1 路由行为，新增模块化目录：

```text
demo-app/backend/
├─ app.py
├─ routers/
│  ├─ fixtures_v1.py
│  ├─ ingestion_v2.py
│  └─ evidence_search_v3.py
├─ providers/
│  ├─ synthetic_ocr.py
│  ├─ vivo_general_ocr.py
│  └─ vivo_evidence_llm.py
├─ services/
│  ├─ image_quality.py
│  ├─ segment_index.py
│  ├─ evidence_search.py
│  └─ review_store.py
├─ schemas/
└─ prompts/
```

不要求机械采用完全相同目录，但不得让 provider 和检索业务继续无边界堆入单文件。

---

## P0-5：已有 evidence schema 会阻挡 live OCR

### 观察

远端 `validate_evidence` 将 `confidence` 设为必需字段且强制为 `[0,1]` 数字。这与 vivo live OCR 无 confidence 的已知事实直接冲突。

### 修复

将证据 schema 区分来源：

```text
source_mode = fixture_sidecar | vivo_live_ocr
confidence = number | null
confidence_label = preset_demo | provider_returned | unavailable
```

校验规则：

- fixture/sidecar 可有数值；
- live vivo OCR 若文档/响应未返回 confidence，则必须为 `null`；
- bbox/locator 与 `material_id` 必须始终可追溯；
- 前端按来源显示正确说明。

---

## P0-6：缺少真实合成上传与 OCR 接线

### 观察

远端上传仅传递文件名和 fixture id，不能证明现场拍摄/上传的合成材料能进入系统。

### 修复

新增 v2 ingestion：

```text
POST /api/v2/demo/ingestions               multipart synthetic image
GET  /api/v2/demo/jobs/{job_id}
POST /api/v2/demo/evidence/{anchor_id}/reviews
GET  /api/v2/demo/cases/{case_id}/summary
```

验收至少包含：

```text
good synthetic image → 接收真实 bytes → OCR/fallback → 形成带 bbox evidence
blurred synthetic image → retake_required
```

---

## P0-7：缺少 v0.9 “证据联查”能力

### 观察

远端无 `DocumentSegment`、无 evidence search API、无 provider status，前端也尚无已证明存在的证据联查界面。

### 修复

新增 v3：

```text
POST /api/v3/demo/cases/{case_id}/segments/rebuild
POST /api/v3/demo/evidence-search
GET  /api/v3/demo/providers/status
POST /api/v3/demo/providers/vivo/smoke-test
```

实现链路：

```text
DocumentSegment 本地索引
→ 查询词与受控同义词召回
→ vivo LLM 可选 grounded rerank
→ 每条结果绑定 segment_id / bbox / material
→ 点击结果回到原图高亮
```

---

## P0-8：vivo OCR 的 HTTP 地址需要明确风险控制

### 观察

已提供文档中的 OCR URL 为 HTTP，且请求携带 Bearer AppKey 和 base64 图片内容。

### 修复

- synthetic-only 前提不得松动；
- 优先以 synthetic 样例测试同路径 HTTPS；
- 若只能 HTTP，完成报告、README 和界面模式信息中必须披露仅限合成 Demo；
- 外部 API 调试不得存储 raw request/response；
- 真实病例阶段绝对不可沿用该调用方式。

---

## P1-1：前端 `App.tsx` 规模过大

### 观察

GitHub 文件信息显示远端 `demo-app/frontend/src/App.tsx` 已达到约 1228 行。继续加入采集、步骤条、证据搜索、bbox overlay、核验、摘要与 provider 状态，会使单文件迭代风险快速上升。

### 修复

在不破坏现有演示的前提下，先抽出新功能相关组件：

```text
features/capture/
features/evidence/
features/search/
features/review/
features/summary/
```

无需为了“重构漂亮”重写现有全部界面；目标是让新功能可测试、可维护。

---

## P1-2：`.gitignore` 还需增加第三方 API 调试防泄漏项

### 已有良好基础

远端 `.gitignore` 已包含：

```text
.env
.env.*
runtime/
demo-app/backend/runtime/
*.sqlite
*.sqlite3
*.db
*.log
real-data/
uploads/
private-records/
```

### 仍需补充

```gitignore
*vivo_api_raw_request*
*vivo_api_raw_response*
*external_api_debug*
*.http-response
```

另外在完成前运行 tracked-file 扫描，防止密钥已经被误提交而 `.gitignore` 无法补救。

---

# 5. 新 Codex 推荐实施顺序

| 顺序 | 任务 | 判定完成条件 |
| ---: | --- | --- |
| 0 | 检查并保留前一 Codex 未提交工作 | 无 destructive reset；报告发现内容 |
| 1 | 写入 PRD 与云端审查文档，修订 AGENTS/agent/skills 冲突 | 规则与 v2/v3/vivo 行为一致 |
| 2 | 保持 v1 基线测试通过 | 旧时间轴演示不回归 |
| 3 | 完成 v2 synthetic ingestion + OCR/bbox/review | 真上传合成图能高亮证据 |
| 4 | 完成 vivo OCR provider 与透明 fallback | `pos=2`、无虚构 confidence、HTTP 风险披露 |
| 5 | 完成 DocumentSegment 与本地证据检索 | 无 LLM 时可完成查询演示 |
| 6 | 接入 vivo LLM grounded rerank | 仅候选片段、有效 segment_id、失败 fallback |
| 7 | 前端证据联查与 selected text 关联结果 | 查询/选中两种入口均能回到原图 |
| 8 | 测试、报告、安全扫描、push | 真实记录并更新 public repo |

---

# 6. 交付前检查清单

## 功能

- [ ] `转诊迹` 品牌在 README、页面、后端服务 title 中一致；
- [ ] v1 fixtures 时间轴仍可用；
- [ ] v2 接受真实合成图片字节并处理；
- [ ] vivo OCR/fallback 与 bbox 展示可区分；
- [ ] live vivo OCR 不展示虚构 confidence；
- [ ] 医生核验可保存；
- [ ] v3 证据联查支持问题输入与选中片段；
- [ ] LLM 输出始终绑定来源 segment；
- [ ] 任何失败都能透明降级而不是白屏/假成功。

## 安全

- [ ] 只处理 synthetic materials；
- [ ] 所有演示图带明显水印；
- [ ] `.env` 不被跟踪；
- [ ] AppKey 不进入代码、前端 bundle、日志或报告；
- [ ] runtime / DB / raw API data 不被跟踪；
- [ ] OCR HTTP 限制已披露；
- [ ] UI 与 README 不出现医学诊断/治疗承诺。

## 验证

- [ ] 后端测试通过；
- [ ] 前端 lint/typecheck/unit/build 通过；
- [ ] Playwright / 浏览器演示链路通过；
- [ ] 若有凭证，synthetic-only vivo smoke test 结果真实记录；
- [ ] push 到现有 public `zgcHack`，且能够从 GitHub 页面看到最新文档和功能。

---

## 7. 云端审查结论

当前远端版本是一个合格的**合成 fixture 时间轴展示基线**，其 public synthetic-only 边界已经部分写入规则文件，也具备测试与前后端分离基础。但它尚未呈现你们今晚新增的真正差异化能力：

```text
现场合成材料采集
+ vivo OCR 坐标证据
+ 医生证据联查
+ BlueLM grounded 关联归纳
+ 医生核验闭环
```

新 Codex 最重要的不是重做页面，而是：

1. 保护上一实例未推送的成果；
2. 修复旧 agent/skill 与新接口契约冲突；
3. 保留 v1 作为稳定 fallback；
4. 用 v2/v3 增量实现可信、可核验、可演示的新闭环；
5. 在 public 仓库中始终保持 synthetic-only 与密钥安全。
