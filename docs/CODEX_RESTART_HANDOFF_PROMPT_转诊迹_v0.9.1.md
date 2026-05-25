# 转诊迹 / zgcHack：新 Codex 接管执行 Prompt（v0.9.1 Resolved）

> **使用方式**：将本文件、`CLOUD_AUDIT_AND_FIX_GUIDE_转诊迹_v0.9.1.md`、`PRD_V0_9_1_VIVO_API_RESOLVED_PATCH_转诊迹_Codex立即追加.md` 一起提供给新的 Codex。  
> **目标仓库**：现有 public 仓库 `WangSibothunder/zgcHack`。  
> **任务性质**：这是接管并继续实现任务，不是重新规划任务。必须审阅现状、保护上一实例可能留下的工作、实现功能、测试、修复并在安全检查后 push。

---

## 你现在接管的项目

产品正式名称为：

```text
转诊迹｜转院病历证据时间轴
把散落病历，连成可核验的转院时间轴。
```

这是一个黑客松 public showcase 项目。系统只处理**带明显水印的合成演示病历材料**，用于展示：

```text
合成材料采集/上传
→ OCR 与材料结构化
→ 按日期构建转院病历时间轴
→ 原文与原图证据定位
→ 医生核验
→ 医生提问/选中文字后的“证据联查”
```

本项目不是诊断系统、治疗推荐系统、分诊系统或医学决策系统。页面、API、README 和路演中均不得输出或宣称诊断结论、病因推断、风险判断、检查建议、用药建议或治疗建议。

---

# 0. 第一原则：先接管现场，绝不能覆盖上一实例的未提交工作

上一位 Codex 可能已经在同一工作区修改 v0.8/v0.9，但远端 GitHub `main` 目前仍可能只显示基础 Demo。开始任何改动前，必须执行并阅读输出：

```bash
pwd
git remote -v
git status --short --branch
git branch -vv
git log --oneline --decorate --graph --all -20
git diff --stat
git diff --name-status
find docs -maxdepth 1 -type f | sort
find .codex/skills -maxdepth 2 -name SKILL.md | sort
```

如果存在未提交修改、未 push commit 或新增文档：

- 不得执行 `git reset --hard`；
- 不得执行 `git clean -fd`；
- 不得重新 clone 覆盖当前目录；
- 不得因远端 main 旧而删除本地新实现；
- 先审阅 diff，将可用工作纳入本轮实现，并在完成报告说明接管时发现的已有改动。

如果当前环境只有远端基础版本，再从该版本按本文与随附 PRD 增量实现。

---

# 1. 必须先读的文件及优先级

## 1.1 阅读顺序

开始代码修改前，逐一读取：

```text
AGENTS.md
agent.md
.codex/skills/product-scope/SKILL.md
.codex/skills/frontend-timeline/SKILL.md
.codex/skills/backend-mock-api/SKILL.md
.codex/skills/synthetic-medical-data/SKILL.md
.codex/skills/evidence-traceability/SKILL.md
.codex/skills/demo-delivery-loop/SKILL.md

README.md
docs/API_CONTRACT.md
docs/SYNTHETIC_DATA_POLICY.md
docs/DEMO_ACCEPTANCE.md
docs/DEMO_COMPLETION_REPORT.md

docs/PRD_V0_8_ZHUANZHENJI.md                         # 若工作区已有
docs/PRD_V0_9_EVIDENCE_LINKED_SEARCH.md               # 若工作区已有
docs/PRD_V0_9_1_VIVO_API_RESOLVED_PATCH.md            # 本次随附，需写入仓库
docs/CLOUD_AUDIT_AND_FIX_GUIDE_转诊迹_v0.9.1.md       # 本次随附，需写入仓库或据此执行
```

若随附文档当前不在仓库中，请先将其复制到上述 `docs/` 路径，再继续开发。

## 1.2 冲突时的优先级

执行时按以下优先级处理冲突：

```text
合成数据与非诊断安全边界（始终最高）
> docs/PRD_V0_9_1_VIVO_API_RESOLVED_PATCH.md
> docs/PRD_V0_9_EVIDENCE_LINKED_SEARCH.md
> docs/PRD_V0_8_ZHUANZHENJI.md
> CLOUD_AUDIT_AND_FIX_GUIDE
> AGENTS.md / agent.md 中仍适用的基础规则
> 旧 docs/API_CONTRACT.md 与旧 skills 的 v1/mock 限定
```

尤其注意：远端现有 `AGENTS.md`、`agent.md` 和部分 skill 是基础 Demo 时期规则，存在需要主动修订的冲突，而不是必须机械遵守的最终产品规格。

---

# 2. 如何使用 AGENTS.md 与 Skills：先继承，再更新冲突规则

## 2.1 `AGENTS.md` 与 `agent.md`

- `AGENTS.md` 是 Codex 实际应读取并遵循的仓库级指令入口。
- `agent.md` 是团队人工阅读副本，内容应与 `AGENTS.md` 保持同步。
- 保留其中已正确的规则：产品聚焦转院场景、public synthetic-only、非诊断边界、测试后再 push。
- 在实现功能前，修订两处已知过时冲突：

### 必须修订 A：API 版本规则

旧规则若写：

```text
All API paths should be versioned below /api/v1/demo/
```

改为：

```text
Keep existing `/api/v1/demo/` fixture browsing endpoints backward-compatible.
Use `/api/v2/demo/` for real-byte synthetic ingestion, camera capture, processing jobs,
evidence review and summary features introduced in v0.8.
Use `/api/v3/demo/` for evidence-linked search, provider status and vivo API smoke-test
features introduced in v0.9/v0.9.1.
Do not silently break an existing response shape; update docs, frontend adapters and tests together.
```

### 必须修订 B：OCR confidence 规则

旧规则若要求每个 evidence 永远必须存在 `OCR confidence`，改为：

```text
Evidence must expose source material and locator information.
For fixture/sidecar data, a clearly labelled preset demo confidence may be shown.
For live vivo OCR, the provided official contract returns text/location but does not specify
an OCR confidence field; store and display `confidence=null` with an honest notice instead of
inventing a numeric confidence.
```

## 2.2 现有 Skills 的使用与升级方式

必须实际读取并按场景使用原有 skills：

| Skill | 本轮用途 |
| --- | --- |
| `$product-scope` | 决定文案和边界：只做材料整理与证据联查，不做医疗建议 |
| `$frontend-timeline` | 保留时间轴视觉逻辑并增加采集页、证据联查面板、高亮交互 |
| `$backend-mock-api` | 保留 v1 fixture API 和离线 fallback；其“只允许 mock/仅 v1”条款已经过时，必须更新 |
| `$synthetic-medical-data` | 生成带水印的采集样例与“食欲不振/食欲欠佳/纳差”证据检索测试数据 |
| `$evidence-traceability` | 实现 bbox、高亮、来源回跳、核验状态；修订 live OCR 必须 confidence 的旧约束 |
| `$demo-delivery-loop` | 启动、测试、E2E、安全扫描、完成报告、push |

为避免后续 Codex 再次误解，新增两个技能，或将其等价内容写入已有 skill 并保证清晰：

```text
.codex/skills/vivo-api-providers/SKILL.md
.codex/skills/evidence-linked-search/SKILL.md
```

新技能至少覆盖：

- vivo OCR/LLM 的环境变量、synthetic-only、provider/fallback 透明披露；
- DocumentSegment → 本地召回 → LLM grounded rerank → 原图证据回跳；
- API 错误、额度、HTTP OCR endpoint 风险与安全降级；
- 不使用 Function Calling 完成本轮主链路。

---

# 3. 接管后第一轮必须产出的状态报告

不要先写大段解释；执行检查后，在当前任务日志/回复中给出简洁表格：

```text
当前分支 / HEAD:
是否发现上一 Codex 未提交改动:
远端 main 是否领先/落后:
已存在 PRD 文件:
当前前端/后端可启动状态:
当前已实现到 v0.8 / v0.9 / v0.9.1 的哪一步:
接下来立即修改的文件:
```

然后直接开始代码实现，不等待用户再次确认。

---

# 4. 已核实的 vivo 接口事实：必须落实，不再留 placeholder

完整接口约束见随附 `docs/PRD_V0_9_1_VIVO_API_RESOLVED_PATCH.md`。以下为不能遗漏的工程决策摘要。

## 4.1 vivo 通用 OCR Provider

已知接口：

```text
POST http://api-ai.vivo.com.cn/ocr/general_recognition
Header:
  Authorization: Bearer <AppKey>
  Content-Type: application/x-www-form-urlencoded
Query:
  requestId=<uuid>
Form Body:
  image=<base64 编码的 jpg/png/bmp>
  pos=2
  businessid="aigc" + AppId
  sessid=<uuid，可选>
```

实现要求：

- 新增/完成 `VivoGeneralOCRProvider`；
- 对现场合成材料固定请求 `pos=2`，因为需要文字和坐标；
- 将返回位置转换为统一 `OCRBlock` / `bbox` / `polygon` 数据；
- 保存并处理 `angle`；
- 文档未提供 live OCR confidence 字段，因此 live 结果 `confidence=null`，UI 显示“位置由 vivo OCR 返回；接口未提供识别置信度”；
- 先用 synthetic 样例验证同路径 `https://` 是否可调用；若只能使用 HTTP，只能用于 synthetic demo，并在 UI/README/完成报告中披露传输限制；
- 严禁将 AppKey、图片 base64 或原始第三方 response 提交或输出到日志。

## 4.2 vivo Chat Completions Provider

已知接口：

```text
POST https://api-ai.vivo.com.cn/v1/chat/completions
Header:
  Authorization: Bearer <AppKey>
  Content-Type: application/json
Protocol:
  OpenAI-compatible Chat Completions
```

模型由 `.env` 配置。优先 smoke test：

```text
qwen3.5-plus + enable_thinking=false
```

若无权限或结构化输出表现不稳定，允许切换：

```text
Volc-DeepSeek-V3.2 + reasoning_effort=minimal
```

工程要求：

- 实现 `VivoEvidenceLLMProvider`；
- 只使用 `stream=false`；
- 只发送医生问题和本地已召回的 Top-K synthetic `DocumentSegment`，不得发送全部病例或图片；
- 文档表格写 `requestId`，官方示例使用 `request_id`：默认先使用 `request_id`；若 synthetic smoke test 返回参数缺失错误 `1001`，最多兼容重试一次 `requestId`，并将有效字段记录到完成报告；
- `1007` 审核干预、`30001` 权限/限流、`2003` 单日限额、timeout 或 schema 失败时，透明 fallback 到本地证据检索；
- 不使用 Function Calling 完成本轮功能。

---

# 5. 本轮必须完成的产品闭环

## 5.1 若 v0.8 工作未完成，先补齐真实采集合成材料链路

必须至少完成：

```text
真实字节上传带水印合成图片
→ runtime 安全存储（已被 gitignore）
→ 图片质量检测（清晰样例可通过；模糊样例提示重拍）
→ OCR provider / fallback
→ 文本与位置进入时间轴材料详情
→ 原图证据高亮
→ 医生确认/需复核/纠正状态可保存
```

摄像头单帧采集若已实现则保留并修复；若尚未实现且时间紧，应在完成真实图片上传、OCR、高亮、证据联查之后再补摄像头，不得因摄像头阻塞核心路演链路。

## 5.2 v0.9/v0.9.1 核心：证据联查

必须实现两个入口：

### A. 医生问题入口

示例输入：

```text
病人最近的材料中是否提到食欲不振？
```

页面只输出：

- 关联文档日期；
- 文档类型/科室（原材料有则显示）；
- 原文片段；
- 一句严格基于原文的材料归纳；
- 相关性标签；
- 当前 provider 模式；
- `查看原图证据`。

无结果时写：

```text
在当前已上传材料中未检索到明确相关记载。
这仅表示现有材料中未找到相关证据，不代表患者不存在该情况。
```

### B. 选中内容入口

医生选中某页、某段 OCR 或某个字段后，显示小字形式的：

```text
关联记录（N）
日期｜材料类型｜相关原文片段｜查看证据
```

点击后应联动时间轴节点与原图 bbox 高亮。

## 5.3 检索与 LLM 架构必须 grounded

严格流程：

```text
OCR blocks
→ DocumentSegment（带 material_id/node_id/date/raw_text/bbox）
→ 本地关键词/受控同义词召回
→ LLM 仅 rerank + 一句 evidence_summary
→ 校验返回 segment_id 必须来自候选集合
→ 前端显示原文片段并可回到原图证据
```

禁止：

- 把整份病例直接给模型自由回答；
- 展示没有 segment 来源的模型文本；
- 用 LLM 输出替代原文；
- 输出诊断或治疗建议。

---

# 6. 立即需要修订/新增的代码与文档

在检查当前工作区实际文件后，以最小侵入方式完成下列内容：

## 6.1 规则和文档

```text
AGENTS.md                                      # 更新 API 版本和 confidence 规则
agent.md                                       # 与 AGENTS.md 同步
README.md                                      # 品牌、外部 API 模式、synthetic-only、路演
.env.example                                   # vivo 配置占位与开关
.gitignore                                     # 添加 raw API 调试响应等忽略项
docs/PRD_V0_9_1_VIVO_API_RESOLVED_PATCH.md
docs/VIVO_API_VERIFICATION.md
docs/API_CONTRACT_V2.md                       # 若 v0.8 API 存在
docs/API_CONTRACT_V3.md                       # 证据联查/provider status/smoke-test
docs/PUBLIC_DATA_POLICY.md
docs/DEMO_V0_9_1_COMPLETION_REPORT.md
```

## 6.2 后端

不要继续将所有新逻辑都堆入原始单文件 `app.py`；在保留现有 v1 endpoint 向后兼容的前提下拆分：

```text
routers/ingestion_v2.py
routers/evidence_search_v3.py
providers/vivo_general_ocr.py
providers/vivo_evidence_llm.py
providers/synthetic_ocr.py
services/image_quality.py
services/segment_index.py
services/evidence_search.py
services/review_store.py
prompts/vivo_evidence_linked_search_system.txt
```

目录名称可适配当前工程，但职责必须分离。

## 6.3 前端

若当前 `App.tsx` 仍是单体大组件，在不导致大范围回归的前提下拆出最必要模块：

```text
features/capture/CaptureWorkbench.tsx
features/timeline/TimelineView.tsx
features/evidence/EvidenceModal.tsx
features/evidence/EvidenceCanvas.tsx
features/search/EvidenceSearchPanel.tsx
features/review/ReviewActions.tsx
features/summary/PreConsultSummary.tsx
```

必须可见：

- `转诊迹` 品牌；
- 合成材料/非诊断提示；
- 上传与处理进度；
- provider 真实模式标签；
- 证据联查框与结果；
- 原图高亮；
- 医生核验状态；
- 外部 API 失败时的透明 fallback。

---

# 7. 合成数据与测试素材

新增全合成、带明显水印的可打印/上传素材，至少覆盖：

```text
清晰材料：能通过质量检测并产生 OCR/sidecar 坐标
模糊材料：必须触发重拍提示
食欲证据材料：
  - “纳差 3 日”
  - “近一周食欲欠佳，进食量较前减少”
  - “食欲不振，否认明显呕吐”
无关材料：不得被错误当作明确证据
```

所有图片需可见：

```text
合成演示材料 / SYNTHETIC DEMO DOCUMENT / 不对应真实患者
```

---

# 8. 验收、测试与 push

## 8.1 自动测试

至少覆盖：

- 旧 v1 fixture 浏览功能无回退；
- multipart synthetic upload；
- 质量检测 pass/retake；
- vivo OCR mock 响应映射、bbox、`confidence=None`；
- `synthetic=false` 不可调用外部 provider；
- vivo LLM mock grounded JSON、非法 segment 丢弃、错误码 fallback；
- 证据联查同义召回；
- 前端搜索结果与 evidence overlay；
- UI 不出现诊断/治疗建议；
- `.env`/key/runtime/raw API response 不被跟踪。

## 8.2 合成 live smoke test

只有在本地有凭证时，且仅对合成材料运行。需要真实记录：

- HTTPS OCR 路径是否可用；若不可用是否仅 synthetic 使用 HTTP；
- OCR `pos=2` 坐标尺度与 overlay 是否正确；
- vivo LLM 实际成功模型；
- `request_id` 或 `requestId` 哪个可用；
- provider 失败时 fallback 是否仍可演示。

不要将 AppKey 发到聊天消息、日志或完成报告。

## 8.3 交付动作

通过测试并安全扫描后：

```bash
git status --short
git diff --stat
git ls-files | grep -Ei '(^|/)\.env($|\.)|runtime|sqlite|\.db$|vivo_api_raw|external_api_debug|real-data|private-records' || true
git grep -nEi 'AppKey\s*=\s*["'\''][^"'\'']+|VIVO_APP_KEY\s*=\s*[^[:space:]]+' -- . ':!*.example' || true
```

确认无敏感内容后，进行小而清晰的 commits，并 push 到**现有 public 仓库** `WangSibothunder/zgcHack`。不得创建新仓库或改成 private。

---

# 9. 完成时必须返回的结果格式

完成后，不要只说“完成了”。请返回：

```markdown
## 接管与保留情况
- 接管时发现的已有本地改动：
- 如何保留/整合上一 Codex 的工作：

## 实现完成度
- v0.8 采集/OCR/高亮/核验：
- v0.9 证据联查：
- v0.9.1 vivo OCR：
- v0.9.1 vivo LLM：
- 当前 fallback 模式：

## 真实测试记录
- 后端：
- 前端：
- E2E：
- synthetic live smoke（若运行）：

## 安全与边界检查
- public 仓库敏感数据扫描：
- `.env`/AppKey/runtime 状态：
- 页面非诊断提示：

## Git 交付
- commits：
- push 结果：
- 尚存限制：
```

若某项没有完成，必须明确写明阻塞和当前仍可运行的 fallback，不得虚构通过结果。
