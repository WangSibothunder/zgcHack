# 转诊迹｜zgcHack v0.8 下一版本迭代需求文档（Codex 执行版）

> **产品名称**：转诊迹  
> **产品副标题**：转院病历证据时间轴  
> **一句话口号**：把散落病历，连成可核验的转院时间轴。  
> **适用仓库**：`WangSibothunder/zgcHack`（仓库保持 public）  
> **版本目标**：从“预置合成病例交互展示 Demo”升级为“支持真实上传/摄像头采集合成材料、自动处理并可由医生核验的流程 Demo”  
> **核心约束**：本版本仍仅使用合成演示材料，禁止接入、上传或提交任何真实患者资料。

---

## 0. Codex 开始执行前必须阅读的说明

请将本文件放入仓库 `docs/PRD_V0_8_ZHUANZHENJI.md`，并由 Codex 在开始实现前完整阅读以下文件：

```text
README.md
AGENTS.md
docs/API_CONTRACT.md
docs/DEMO_ACCEPTANCE.md
docs/DEMO_COMPLETION_REPORT.md（若存在）
demo-app/backend/app.py
demo-app/frontend/src/App.tsx
demo-app/frontend/src/types.ts
demo-app/frontend/src/api.ts
demo-data/cases/
.codex/skills/
```

### 0.1 本轮不是重新做一个项目

必须在当前已有功能上增量实现，保留以下现有能力且不得回退：

- 3 套合成转院病例可选择浏览；
- 心内科病例至少 6 个按日期排序的节点；
- 横向时间轴、详情面板、材料预览、OCR 文本和证据弹窗；
- “只看异常”“与转院原因相关”“材料类型”筛选；
- 空结果、加载失败、低置信度等反馈；
- 前端通过 HTTP API 访问后端；
- 现有测试可以继续运行或被等价的新测试覆盖；
- 页面持续显示“合成演示数据，仅用于材料整理演示，不构成诊断或治疗建议”。

### 0.2 public 仓库策略是确定需求，不是问题

当前 GitHub 仓库**就是要保持 public**，用于展示黑客松作品、工程过程与合成数据 Demo。Codex 不得将其改成 private，也不得在文档中写成 private。

public 仓库的红线如下：

- 只能提交虚构病例、合成图片、合成 OCR、模拟账号与示例配置；
- 禁止提交真实病历、真实报告截图、真实患者姓名/就诊号/联系电话/住址、真实 OCR 内容；
- 禁止提交 API Key、`.env`、token、cookie、本地运行时上传目录、数据库运行文件；
- 若实现上传功能，上传产生的文件、OCR 缓存、SQLite 数据库和日志必须写入 `.gitignore` 覆盖的运行时目录；
- README 必须明确：公开仓库只展示合成材料流程，未来真实材料需要独立合规环境。

---

# 1. 产品命名决策

## 1.1 最终推荐名称：转诊迹

### 标准展示方式

```text
转诊迹
转院病历证据时间轴
把散落病历，连成可核验的转院时间轴。
```

### 英文处理方式

黑客松阶段不要急于注册或强化英文品牌。代码、API 或页面辅助标识可暂用：

```text
ZhuanZhenJi Demo
Transfer Record Evidence Timeline
```

其中 `ZhuanZhenJi Demo` 仅作为代码/演示标识，不代表已完成英文商标核验。

## 1.2 为什么选择“转诊迹”

| 判断维度 | 分析 |
| --- | --- |
| 场景关联 | “转诊”直接指向患者从外院转入新医院的场景，不会被误解成普通健康管理 App。 |
| 价值表达 | “迹”同时表达病历轨迹与证据痕迹，贴合时间轴和可追溯能力。 |
| 记忆成本 | 三个汉字，读音明确，医生、导诊人员和评委容易复述。 |
| 辨识度 | 比“智慧病历”“电子病历助手”“医疗时间轴”等纯描述性名称更有品牌识别性。 |
| 医疗边界 | 名称不承诺自动诊断、治疗推荐或风险预测，符合本项目“材料整理 + 证据核验”的定位。 |
| 产品延展 | 可自然形成“转诊迹·采集台”“转诊迹·医生视图”“转诊迹·证据轴”等模块命名。 |

## 1.3 不采用的候选名称

| 候选名称 | 不采用原因 |
| --- | --- |
| 医序 | 过于宽泛，容易被理解为医院流程或健康管理系统；公开搜索中已出现相关医疗使用痕迹。 |
| 脉序 | 在医学影像语境中可能与扫描“序列/脉序”含义混淆，场景指向不够准确。 |
| 诊迹 | 简洁但比“转诊迹”少了核心场景限定；用于商业扩展可以保留为备选。 |
| MedTrace / CareLink 等英文泛名 | 医疗行业使用密度高，且未完成系统性的中英文近似商标核验，不适合当前直接定为主品牌。 |

## 1.4 命名落地修改清单

Codex 必须完成以下品牌替换，但**不要重命名 GitHub 仓库**，仓库地址继续保持 `zgcHack`：

- 页面浏览器标题修改为：`转诊迹｜转院病历证据时间轴 Demo`
- 页面左上角品牌修改为：`转诊迹`
- 页面主标题修改为：`转院病历证据时间轴`
- 页面副标题/口号增加：`把散落病历，连成可核验的转院时间轴。`
- README 标题修改为：`# 转诊迹（zgcHack）｜转院病历证据时间轴 Demo`
- FastAPI title 修改为：`转诊迹 Synthetic Demo API`
- API 返回的 `service` 可修改为：`zhuanzhenji-demo-api`
- 文档中的“产品名称”统一写为“转诊迹”；仓库名、路径或旧版本说明可保留 `zgcHack`

---

# 2. 当前版本基线判断

当前仓库已经完成 v0.5 级别的展示闭环：

- React + TypeScript 前端；
- FastAPI 后端；
- 后端读取 `demo-data/` fixtures；
- 前端从 API 获取病例和时间轴；
- 三位合成患者；
- 时间轴节点详情、OCR、证据展示与筛选；
- 当前上传为模拟流程：仅发送文件名和 fixture 选择器，并不真正读取文件内容；
- 当前证据定位主要是 `locator_text`/`page_or_image` 描述，尚未在原图坐标区域中绘制高亮框；
- 当前 `verification_status` 为预置状态，尚未形成医生确认、纠正和审计闭环。

**本轮目标不是删除 mock 功能，而是增加一个真正可演示的 Synthetic Live Processing 模式。**

---

# 3. v0.8 产品目标与路演主线

## 3.1 本版本成功标准

评委应能现场看到以下完整流程：

```text
打开“转诊迹”首页
→ 查看已有合成病例时间轴
→ 切换到“采集新材料”页面
→ 使用摄像头拍摄或上传一张合成病历图片
→ 系统进行图片质量检测
→ 模糊/反光材料被提示重新拍摄
→ 合格材料进入 OCR 与字段抽取
→ 自动识别日期和材料类型
→ 在新的或现有合成病例时间轴中生成/插入节点
→ 点击结构化字段，在原图中看到对应高亮证据框
→ 医生选择“确认正确 / 标记需复核 / 修改字段”
→ 系统保存核验记录并生成接诊前整理摘要
```

## 3.2 本版本只处理的业务范围

仅处理：

- 合成病历照片；
- 合成检查/检验报告图片；
- 合成出院小结或门诊记录；
- 合成 PDF 可作为 P1，若工期紧张则先支持 JPG/PNG；
- 时间排序、材料分类、少量字段提取、证据绑定、医生核验；
- 结果均属于“材料整理结果”，不属于医学判断。

明确不处理：

- 真实患者数据；
- 诊断建议；
- 治疗方案推荐；
- 危重风险判断；
- 转院去向推荐；
- 医院 HIS/EMR 实际接入；
- 大模型自由生成临床总结。

---

# 4. 页面信息架构与新增交互

## 4.1 页面导航

在当前单页时间轴体验基础上，增加三个顶部 Tab：

```text
[医生时间轴]  [采集新材料]  [接诊前摘要]
```

### A. 医生时间轴

保留现有页面能力，并新增：

- 原图 bbox 高亮；
- 核验状态操作；
- 新上传节点标识；
- 处理来源标识：`预置演示数据` / `现场合成材料处理`；
- 关键字段的“已确认 / 需复核 / 已修改”视觉状态。

### B. 采集新材料

新增采集工作台，包含：

- 选择演示患者 / 创建新的合成接诊批次；
- 文件上传区域；
- 摄像头拍照按钮；
- 合成数据警示条；
- 拍摄质量反馈；
- 处理步骤进度条；
- 失败后重新拍摄 / 删除该页；
- 处理完成后“前往时间轴查看”按钮。

### C. 接诊前摘要

展示由结构化材料整理得到的简洁摘要：

- 转院路径；
- 材料覆盖时间；
- 与转院原因相关的关键时间节点；
- 含标记字段的材料列表；
- 尚未核验的字段数量；
- 可能缺少的材料类别提示；
- 导出为打印友好页面按钮（P1）；
- 固定提示：摘要仅用于材料整理和核验，不构成诊断结论。

---

# 5. P0 必做功能需求

> P0 是本轮交付的硬性完成条件。任何 P0 未完成，不得在报告中写“v0.8 完成”。

## FR-P0-01 品牌升级

### 需求

将 UI 与 README 中面向用户的产品名称统一为“转诊迹”。

### 验收

- 浏览器页面 title、顶部品牌、README 标题、后端服务 title 均更新；
- 页面可见副标题“转院病历证据时间轴”；
- 页面可见口号“把散落病历，连成可核验的转院时间轴。”；
- GitHub 仓库路径继续为 `zgcHack`；
- README 明确仓库为 public synthetic demo。

---

## FR-P0-02 真正上传合成文件内容

### 需求

现有 `POST /api/v1/demo/uploads` 是 fixture simulation，必须保留以保证旧演示可复现；同时新增真实接收合成文件内容的接口。

### 前端

在“采集新材料”页支持：

- 上传 `.png`、`.jpg`、`.jpeg`；
- 单次最多 10 张，每张最大 10 MB；
- 页面明确提醒只能上传合成演示材料；
- 选择文件后显示缩略图、文件名和移除按钮；
- 点击“开始处理”后发送真实二进制文件，而不是只发送文件名。

### 后端

新增 API：

```http
POST /api/v2/demo/ingestions
Content-Type: multipart/form-data
```

请求字段：

```text
files: UploadFile[]
case_id: string | optional
source: "upload" | "camera"
synthetic_acknowledged: true
```

响应：

```json
{
  "job_id": "ingest-20260525-001",
  "status": "uploaded",
  "synthetic": true,
  "message": "合成演示材料已接收，开始处理。"
}
```

### 数据存储

所有上传文件仅写入运行时目录：

```text
runtime/uploads/{job_id}/
runtime/jobs/
runtime/reviews/
runtime/generated_cases/
```

并确保：

```gitignore
runtime/
demo-app/backend/runtime/
*.sqlite3
*.db
.env
.env.*
```

### 验收

- 上传后的图片字节确实被后端读取并保存到被忽略的 runtime 目录；
- 现有 fixture 模拟上传仍可用；
- 提交到 Git 的文件中不存在运行时上传内容。

---

## FR-P0-03 摄像头拍照采集合成材料

### 需求

前端增加桌面摄像头/普通 USB 文档摄像头采集入口，用于黑客松现场演示。

### 实现要求

- 使用浏览器 `navigator.mediaDevices.getUserMedia({ video: true })`；
- 用户点击“开启摄像头”后才请求权限；
- 摄像头画面仅本地预览，不持续上传视频流；
- 用户点击“拍摄本页”后，将单帧转换为图片 Blob 并提交给同一 ingestion API；
- 页面写明：请只拍摄提供的合成演示材料；
- 权限拒绝时提供友好提示，并允许切换到文件上传。

### 验收

- 允许从摄像头采集一帧合成材料并进入处理流程；
- 禁止后台持续录像；
- 失败时不影响上传文件模式。

---

## FR-P0-04 图像质量检测与重拍反馈

### 需求

系统必须让评委看到：它不会对明显无法读取的材料假装确定。

### 检测项目

P0 至少实现：

1. 模糊检测；
2. 过度曝光/大面积反光提示；
3. 图片过小或不支持格式提示。

P1 可追加：

- 页面边缘检测；
- 透视矫正；
- 旋转方向识别；
- 重复页检测。

### 后端输出模型

```json
{
  "material_id": "runtime-mat-001",
  "quality": {
    "status": "pass | retake_required | warning",
    "blur_score": 82.4,
    "glare_ratio": 0.031,
    "messages": [
      "检测到明显模糊，建议重新拍摄后再识别。"
    ]
  }
}
```

### UX 要求

- `retake_required`：不进入后续 OCR，页面突出显示“需重拍”；
- `warning`：允许继续处理，但标注“可能影响 OCR 准确性”；
- `pass`：进入 OCR；
- 文案只谈图像质量，不谈患者病情。

### 演示资产

必须在 `demo-data/capture-samples/` 提供：

```text
good_lab_report.png        # 清晰合成材料，可通过
blurred_lab_report.png     # 故意模糊，应提示重拍
glare_lab_report.png       # 故意高亮遮挡，应至少 warning 或重拍
```

### 验收

- 上传 `blurred_lab_report.png` 会显示需重拍；
- 上传 `good_lab_report.png` 可进入 OCR 与时间轴；
- 质量阈值放入配置文件或常量并有注释，不能散落硬编码。

---

## FR-P0-05 OCR 结果与 bounding boxes

### 需求

当前系统只有预置 OCR 文本。本版本需要为现场合成材料处理模式生成 OCR 文本块与坐标，以支撑证据高亮。

### 技术原则

采用可替换 provider 架构，不把系统锁死在某一个 OCR 库：

```python
class OCRProvider(Protocol):
    def recognize(self, image_path: Path) -> OCRResult:
        ...
```

至少实现两种运行方式：

1. `PaddleOCRProvider`：环境允许安装/下载模型时，对合成图片执行真实 OCR；
2. `DeterministicSyntheticProvider`：在现场无网络或模型下载失败时，从与合成演示图片一一对应的 sidecar JSON 读取确定性 OCR 与 bbox。

**界面必须透明披露当前模式：**

- 真实 OCR 模式：`OCR 引擎处理`
- fallback 模式：`预置合成 OCR 演示回放`

不得在 fallback 模式下伪称执行了真实 OCR。

### OCR 数据结构

```json
{
  "ocr_mode": "paddleocr | deterministic_synthetic",
  "blocks": [
    {
      "block_id": "ocr-b-001",
      "text": "报告日期：2025-01-15",
      "bbox": [86, 110, 512, 152],
      "confidence": 0.97
    },
    {
      "block_id": "ocr-b-002",
      "text": "肌钙蛋白 I：0.19 ng/mL ↑",
      "bbox": [96, 312, 598, 361],
      "confidence": 0.91
    }
  ],
  "full_text": "..."
}
```

`bbox` 统一采用：

```text
[x_min, y_min, x_max, y_max]
```

并基于原始/矫正后图像像素坐标。

### 验收

- 清晰样例能生成 OCR blocks；
- 至少一个关键字段具有可绘制的 bbox；
- 页面展示当前 OCR mode；
- 真实 OCR 依赖不可用时，fallback 可继续演示且标识真实。

---

## FR-P0-06 受限字段抽取与时间轴节点自动插入

### 需求

根据 OCR 内容抽取**材料组织信息**，不生成医学推断。

### P0 可抽取字段

仅限：

- `document_date`：报告/就诊日期；
- `hospital_name`：材料中出现的机构名称；
- `department`：材料中出现的科室；
- `document_type`：门诊记录、检验报告、检查报告、出院小结；
- `source_highlights`：原文中明确标记的数值或表述；
- `transfer_related_text`：原材料中明确出现“转上级医院”“转院”等文字时进行标记。

### 严格边界

允许：

```text
原材料出现：肌钙蛋白 I：0.19 ng/mL ↑
系统输出：原材料包含标记升高字段，待医生核验。
```

禁止：

```text
系统输出：患者可能发生心肌梗死，应立即治疗。
```

### 时间轴规则

- 日期识别成功：按日期插入时间轴；
- 日期无法确定：进入“待确认材料”区域，用户可手动填写日期后插入；
- 同日已有节点：追加材料到同一节点；
- 同日无节点：创建新节点；
- 新生成节点显示 `现场合成材料处理` 和 `新上传` 标签。

### 验收

- 上传清晰合成样例后，能生成或插入对应日期节点；
- 日期识别失败样例不会被错误排序，而是进入待确认区；
- 输出文字不包含诊断结论或治疗建议。

---

## FR-P0-07 原图高亮证据定位

### 需求

当前证据弹窗仅以文字说明位置。本轮必须在图片上绘制对应字段高亮框。

### 数据结构升级

在 `EvidenceAnchor` 中新增：

```json
{
  "anchor_id": "ev-live-001",
  "field_key": "原文标记字段",
  "display_value": "肌钙蛋白 I：0.19 ng/mL ↑",
  "material_id": "runtime-mat-001",
  "ocr_block_ids": ["ocr-b-002"],
  "bbox": [96, 312, 598, 361],
  "ocr_confidence": 0.91,
  "extraction_confidence": 0.90,
  "verification_status": "unreviewed",
  "source_mode": "live_synthetic_upload"
}
```

### 前端交互

- 点击结构化字段或证据项，打开原图弹窗；
- 原图上显示高亮矩形；
- 弹窗中同步显示 OCR 原文、置信度、字段来源、核验状态；
- 图片缩放后高亮框仍与图像坐标正确对齐；
- 预置 fixture 中旧证据若没有 bbox，可保留文字定位，并标注“旧版定位说明”；新增现场处理样例必须具有 bbox。

### 验收

- 现场上传的清晰合成材料至少有一个字段可在原图中高亮；
- 高亮框肉眼能够定位到对应文字行；
- 缩放或响应式布局下不明显偏移。

---

## FR-P0-08 医生核验、纠正与审计记录

### 需求

在合成演示流程中加入医生主导的确认闭环。

### 支持操作

对每个 Evidence Anchor 支持：

- `确认正确`：`confirmed`
- `标记需复核`：`needs_review`
- `修改字段`：保存修改值与修改理由，状态为 `corrected`

### API

```http
POST /api/v2/demo/evidence/{anchor_id}/reviews
Content-Type: application/json
```

请求示例：

```json
{
  "action": "confirmed | needs_review | corrected",
  "corrected_value": "可选，action=corrected 时必填",
  "note": "可选的核验说明",
  "reviewer_role": "接诊医生（演示）"
}
```

响应示例：

```json
{
  "review_id": "review-001",
  "anchor_id": "ev-live-001",
  "action": "confirmed",
  "before_value": "肌钙蛋白 I：0.19 ng/mL ↑",
  "after_value": "肌钙蛋白 I：0.19 ng/mL ↑",
  "reviewed_at": "2026-05-25T12:00:00Z",
  "synthetic": true
}
```

### 持久化方式

Demo 阶段可采用 SQLite 或 JSON file store，写入：

```text
runtime/reviews/
```

不得提交到 Git。

### 验收

- 点击确认后状态在当前页面立即更新；
- 刷新页面后状态仍存在；
- 修改字段后可以查看修改前/修改后内容；
- 可查看至少当前病例的审计列表；
- 审计内容持续标识 synthetic demo。

---

## FR-P0-09 接诊前摘要页

### 需求

提供一个面向医生的“一页式整理结果”，以支撑路演价值表达。

### 页面内容

必须包括：

- 患者为合成演示患者的明显标识；
- 转院路径和目标科室；
- 病历材料覆盖时间；
- 时间节点数量、上传材料数量；
- 与转院原因相关的节点列表；
- 尚未核验/需复核/已确认字段数量；
- 材料缺失整理提示；
- 说明文字：系统仅整理材料和证据，不生成诊断或治疗意见。

### 生成逻辑

摘要内容必须来自当前时间轴结构化数据与核验状态，不允许由 LLM 自由生成医学文字。

### 验收

- 上传合成材料并确认一个字段后，摘要页统计同步更新；
- 缺失材料内容使用“未发现相关材料，建议人工核对是否需要补充”这类组织提示，不写医学必要性结论。

---

## FR-P0-10 测试、文档与 public 数据防护

### 自动化测试必须新增

后端：

- multipart 图片上传成功；
- 不支持格式/超大文件失败；
- `synthetic_acknowledged=false` 拒绝上传；
- 模糊合成样例得到 `retake_required`；
- 清晰样例能够进入 OCR/生成材料；
- timeline 插入新节点或合并同日节点；
- evidence review 写入和重新读取；
- runtime 数据不会被 fixture 校验错误误提交。

前端：

- 品牌名称和安全提示展示；
- 采集页面可选择文件；
- 摄像头权限拒绝时 fallback UI；
- 处理状态步骤展示；
- 质量失败提示；
- 原图 bbox 高亮组件渲染；
- review 操作更新状态；
- 摘要页显示核验计数。

E2E：

```text
进入采集页
→ 上传 good_lab_report.png
→ 查看处理状态完成
→ 返回时间轴看到新增/更新节点
→ 打开证据看到高亮框
→ 点击确认正确
→ 进入摘要页看到已确认数量更新
```

### 文档必须新增或修改

```text
README.md
docs/PRD_V0_8_ZHUANZHENJI.md
docs/API_CONTRACT_V2.md
docs/PUBLIC_DATA_POLICY.md
docs/DEMO_V0_8_ACCEPTANCE.md
docs/DEMO_V0_8_COMPLETION_REPORT.md
```

### public 仓库检查

在交付报告中记录以下检查结果：

```bash
git status --short
git ls-files | grep -Ei 'runtime|\.env|sqlite|\.db|token|secret' || true
```

若命令输出存在不应提交的运行时或密钥文件，必须先移除再 push。

---

# 6. P1 增强功能（P0 完成后继续实现）

P1 不能挤占 P0 的完成时间。P0 全部通过后，按下列顺序实现。

## FR-P1-01 页面自动裁切与透视矫正

- 识别 A4 页面边缘；
- 展示“原图 / 矫正后图片”切换；
- OCR 默认基于矫正后图像；
- 若自动矫正失败，应允许跳过并继续 OCR，不得阻塞演示。

## FR-P1-02 关键字段跨节点趋势展示

仅展示材料原文中出现的同名指标随时间的**原文记录趋势**，例如：

```text
肌钙蛋白 I：2024-05-08（原文值） → 2025-01-15（原文值）
```

注意：

- 只呈现记录值；
- 不输出趋势的医学解释；
- 曲线图旁始终提示“请结合原始报告由医生核验”。

## FR-P1-03 生成补充材料清单

根据材料类型缺失提示生成可复制清单：

```text
未在当前上传材料中发现：
- 冠脉 CTA/造影相关报告
- 某次住院的完整出院记录

说明：以上为材料完整性整理提示，请由接诊人员确认是否需要补充。
```

## FR-P1-04 打印友好摘要页

- 支持浏览器打印；
- 标题含“转诊迹｜合成演示接诊前整理摘要”；
- 带生成时间和 synthetic watermark；
- 不生成 PDF 服务端持久文件，避免 public demo 增加数据管理复杂度。

## FR-P1-05 Demo 重置

新增按钮和 API，将 runtime 上传材料与核验状态恢复为空，便于反复演示：

```http
POST /api/v2/demo/runtime/reset
```

需要明显二次确认，且仅影响 synthetic runtime 数据。

---

# 7. P2 后续商业化方向（本轮不强求实现）

以下内容只需在 README roadmap 中记录，不应阻塞 v0.8：

- 登录、角色权限与访问控制；
- 数据加密、保留时间、删除策略与审计；
- 私有部署或院内部署；
- PDF 多页批量处理；
- 与 FHIR `DocumentReference` 或院内系统的数据映射；
- 医生/导诊人员可用性测试与效率对照试验；
- 针对多类材料的 OCR 和字段抽取准确率评估。

---

# 8. 后端架构建议

## 8.1 目标目录结构

在不破坏当前工程的情况下，建议拆分为：

```text
demo-app/backend/
├─ app.py                         # 应用入口与路由注册
├─ routers/
│  ├─ demo_v1.py                  # 保留现有 fixture API
│  └─ ingestion_v2.py             # 新增上传、任务、review、summary API
├─ services/
│  ├─ storage.py                  # runtime 路径与安全文件保存
│  ├─ image_quality.py            # 模糊/反光/格式检查
│  ├─ ocr_provider.py             # OCRProvider 接口
│  ├─ paddle_ocr_provider.py      # 可选真实 OCR
│  ├─ synthetic_ocr_provider.py   # 可复现 fallback
│  ├─ extractor.py                # 受限字段抽取
│  ├─ timeline_builder.py         # 日期聚合与节点更新
│  └─ review_store.py             # 核验状态/审计
├─ schemas/
│  ├─ ingestion.py
│  ├─ evidence.py
│  └─ timeline.py
├─ runtime/                       # 必须 gitignore
└─ tests/
```

如果 Codex 判断当前规模不足以拆分为完整包结构，可以采用更小的模块划分，但不得继续把所有 v2 逻辑堆入单个 `app.py`。

## 8.2 处理任务状态

任务状态至少包括：

```text
uploaded
quality_checking
retake_required
ocr_processing
extracting_fields
timeline_generated
failed
```

前端可轮询：

```http
GET /api/v2/demo/jobs/{job_id}
```

返回处理中步骤和每页材料状态。

## 8.3 OCR 技术路线

推荐优先尝试 PaddleOCR/PP-OCR 系列处理中文合成文档并保留文字位置；同时实现 deterministic fallback 保证离线现场演示。

注意：

- 不要将大型模型权重提交到 public Git 仓库；
- 下载模型失败不能让整个 Demo 崩溃；
- OCR 模式必须在 UI 中透明显示；
- 字段抽取仅依据 OCR 文字和规则，不要求引入通用 LLM。

---

# 9. 前端组件建议

在现有 `App.tsx` 基础上逐步拆分：

```text
demo-app/frontend/src/
├─ App.tsx
├─ features/
│  ├─ timeline/
│  │  ├─ TimelineView.tsx
│  │  ├─ TimelineRail.tsx
│  │  ├─ DetailPanel.tsx
│  │  └─ EvidenceModal.tsx
│  ├─ capture/
│  │  ├─ CaptureWorkbench.tsx
│  │  ├─ FileDropzone.tsx
│  │  ├─ CameraCapture.tsx
│  │  ├─ QualityResultCard.tsx
│  │  └─ ProcessingStepper.tsx
│  ├─ review/
│  │  ├─ EvidenceCanvas.tsx
│  │  └─ ReviewActions.tsx
│  └─ summary/
│     └─ PreConsultSummary.tsx
├─ api/
│  └─ client.ts
└─ types/
   └─ index.ts
```

## 9.1 EvidenceCanvas 要点

- 使用 `<img>` + absolutely-positioned overlay 绘制高亮框即可；
- 基于图片 naturalWidth/naturalHeight 与展示尺寸计算缩放比例；
- 不要把高亮直接烧录进图片，保留原始图；
- 高亮框旁可显示字段名称和核验状态；
- 支持键盘关闭弹窗与基本无障碍标签。

## 9.2 采集页路演优先级

视觉效果不要过度堆叠。采集页最重要的四个区域是：

1. 合成数据/不构成诊断提示；
2. 摄像头或上传入口；
3. 图片质量检测反馈；
4. 处理步骤与“前往时间轴”按钮。

---

# 10. 数据资产要求

## 10.1 新增合成采集样例

建议新增一套“现场可打印拍摄”的心内科合成资料：

```text
demo-data/capture-samples/
├─ originals/
│  ├─ cardiac_lab_clear.png
│  ├─ cardiac_visit_note_clear.png
│  └─ cardiac_discharge_summary_clear.png
├─ degraded/
│  ├─ cardiac_lab_blurred.png
│  └─ cardiac_lab_glare.png
└─ sidecars/
   ├─ cardiac_lab_clear.ocr.json
   ├─ cardiac_visit_note_clear.ocr.json
   └─ cardiac_discharge_summary_clear.ocr.json
```

### 样例原则

- 页面醒目标注 `合成演示材料 / SYNTHETIC DEMO DOCUMENT`；
- 姓名统一采用 `演示患者 A01`；
- 医院采用虚构名称；
- 材料文字可支撑当前故事线；
- 清晰样例可以打印后由摄像头拍摄；
- sidecar 坐标应与原始图片严格对应；
- degraded 样例只用于质量检测展示。

## 10.2 测试数据不可伪装真实患者

不要使用“张某”“某真实医院名称”等可能造成真实感混淆的信息。统一使用：

```text
演示患者 A01
青禾县中心医院（虚构）
云川医学中心（虚构）
合成演示材料
```

---

# 11. 路演脚本要求

完成 v0.8 后，在 README 增加 3 分钟路演脚本。

## 11.1 主演示流程

```text
1. 首页介绍：这是“转诊迹”，把散落病历整理为可核验的转院时间轴。
2. 浏览预置时间轴：展示既有合成转院病例及证据追溯。
3. 打开采集页：先拍摄/上传故意模糊的合成化验单。
4. 系统反馈：图片模糊，需要重拍，无法可靠识别。
5. 再上传清晰材料：显示质量通过、OCR、字段抽取和时间轴生成进度。
6. 进入时间轴：展示新增材料对应日期节点。
7. 点击关键字段：原图上出现高亮证据框。
8. 医生点击“确认正确”或“标记需复核”。
9. 打开摘要页：展示关键节点、待核验字段与材料缺失提示。
10. 结尾说明：系统只整理与追溯证据，临床判断仍由医生完成。
```

## 11.2 路演中不得表达的内容

不得说：

- “系统诊断出了某疾病”；
- “AI 判断患者必须进行某治疗”；
- “已可直接处理真实病例”；
- “已达到医院部署合规要求”。

可说：

- “本 Demo 使用合成材料验证采集、整理和证据追溯流程”；
- “下一阶段将在合规环境中开展真实用户流程验证”；
- “系统输出为材料组织结果，医生可逐项核验与纠正”。

---

# 12. API Contract v2 草案

## 12.1 创建处理任务

```http
POST /api/v2/demo/ingestions
Content-Type: multipart/form-data
```

响应：

```json
{
  "job_id": "ingest-demo-001",
  "synthetic": true,
  "status": "uploaded",
  "processing_mode": "live_synthetic_upload",
  "created_at": "2026-05-25T12:00:00Z"
}
```

## 12.2 获取任务状态

```http
GET /api/v2/demo/jobs/{job_id}
```

响应示例：

```json
{
  "job_id": "ingest-demo-001",
  "synthetic": true,
  "status": "timeline_generated",
  "steps": [
    {"name": "文件接收", "status": "completed"},
    {"name": "图像质量检测", "status": "completed"},
    {"name": "OCR 识别", "status": "completed", "mode": "paddleocr"},
    {"name": "字段抽取", "status": "completed"},
    {"name": "时间轴生成", "status": "completed"}
  ],
  "generated_case_id": "runtime-case-001",
  "generated_node_ids": ["runtime-node-20250115"]
}
```

## 12.3 获取带高亮证据的材料详情

```http
GET /api/v2/demo/cases/{case_id}/materials/{material_id}
```

响应必须包含：

```json
{
  "image_url": "/runtime-assets/...",
  "ocr_mode": "paddleocr",
  "ocr_blocks": [],
  "evidence_anchors": [
    {
      "anchor_id": "ev-live-001",
      "bbox": [96, 312, 598, 361],
      "verification_status": "unreviewed"
    }
  ]
}
```

## 12.4 提交核验

```http
POST /api/v2/demo/evidence/{anchor_id}/reviews
```

支持 `confirmed`、`needs_review`、`corrected`。

## 12.5 获取接诊前摘要

```http
GET /api/v2/demo/cases/{case_id}/summary
```

返回统计、关键节点和材料完整性提示，不返回诊断或治疗建议。

---

# 13. 完成定义 Definition of Done

## 13.1 P0 功能全部满足

- [ ] 产品名称已更新为“转诊迹”，仓库仍为 public `zgcHack`；
- [ ] 已有 fixtures 浏览流程无回退；
- [ ] 可上传真实字节的合成图片；
- [ ] 可通过摄像头采集单帧合成材料；
- [ ] 模糊样例会被要求重拍；
- [ ] 清晰样例进入 OCR/字段抽取流程；
- [ ] OCR provider 支持真实引擎和诚实标识的 fallback；
- [ ] 现场处理样例生成具有 bbox 的证据；
- [ ] 原图弹窗能显示高亮框；
- [ ] 医生可确认、标记需复核或纠正字段；
- [ ] 核验操作刷新后仍保留；
- [ ] 接诊前摘要页可显示核验统计和缺失材料提示；
- [ ] 全页面持续显示 synthetic 与非诊断边界；
- [ ] runtime/、密钥、真实数据不进入 Git；
- [ ] 后端、前端和 E2E 测试通过；
- [ ] README 与完成报告记录真实命令与真实结果。

## 13.2 交付物

```text
代码实现
更新后的 README.md
docs/PRD_V0_8_ZHUANZHENJI.md
docs/API_CONTRACT_V2.md
docs/PUBLIC_DATA_POLICY.md
docs/DEMO_V0_8_ACCEPTANCE.md
docs/DEMO_V0_8_COMPLETION_REPORT.md
新增合成采集图片与 sidecar 数据
新增/更新的自动化测试
```

## 13.3 Git 提交建议

可按阶段提交，避免一个巨大 commit：

```text
feat(brand): rename product UI to 转诊迹
feat(capture): add synthetic file and camera ingestion workflow
feat(processing): add quality check and OCR provider pipeline
feat(evidence): render bounding-box evidence overlays
feat(review): add doctor verification and audit state
feat(summary): add pre-consult organization summary
test(demo): cover v0.8 ingestion and evidence review flow
docs(demo): publish public synthetic demo v0.8 acceptance report
```

---

# 14. 直接发送给 Codex 的执行指令

将本文件放入仓库后，把下面内容作为 Codex 的首条任务消息发送：

```text
请先读取仓库根目录 AGENTS.md、README.md、docs/PRD_V0_8_ZHUANZHENJI.md、
docs/API_CONTRACT.md、docs/DEMO_ACCEPTANCE.md 和现有前后端代码，然后开始执行
“转诊迹 v0.8”迭代。

重要前提：
1. 当前 GitHub 仓库 zgcHack 是刻意设置为 public 的作品展示仓库，不要改成 private，
   不要创建新仓库；完成后 push 到现有 public 仓库。
2. public 仓库只允许合成数据。禁止引入真实患者病历、真实 OCR 内容、密钥、
   .env、runtime 上传文件、SQLite/数据库运行文件或任何敏感材料。
3. 产品正式展示名称统一为“转诊迹｜转院病历证据时间轴”，口号为
   “把散落病历，连成可核验的转院时间轴。”
4. 保留当前 v1 fixture 时间轴浏览流程，不得回退现有筛选、证据弹窗和测试能力。

本轮必须完成 P0：
- 真正上传合成图片字节的 ingestion v2 接口；
- 浏览器摄像头采集单帧合成材料；
- 模糊/反光质量检测与重拍反馈；
- OCR Provider 架构：可用时接入真实 OCR，不可用时采用明确标注为
  “预置合成 OCR 演示回放”的 deterministic fallback，禁止伪称真实识别；
- 根据合成材料生成/插入时间轴节点；
- evidence bbox 数据与原图高亮框展示；
- 医生“确认正确 / 需复核 / 修改字段”及 runtime 持久化审计；
- 接诊前摘要页；
- API_CONTRACT_V2、PUBLIC_DATA_POLICY、验收清单与完成报告；
- 后端、前端、E2E 测试，并真实记录命令和结果。

执行方式：
持续完成“检查现状 → 实现 → 运行测试 → 修复 → 浏览器验收 → 更新文档 →
检查 public 仓库安全边界 → git commit → push”的闭环。
不要只给建议、TODO 或方案；必须实际修改代码并运行验证。
若模型安装或摄像头权限等外部条件阻塞真实实现，必须提供诚实可运行的 fallback，
在界面和完成报告中标清限制，仍应完成其余 P0 闭环。
```

---

# 15. 本轮开发判断原则

开发中出现取舍时，请遵循下列优先级：

```text
可信证据追溯 > 真实采集闭环 > 医生可控核验 > 页面华丽效果
合成数据安全 > 功能数量
可演示且诚实的 fallback > 无法稳定运行但宣称更智能的功能
材料整理 > 医学推断
```

完成后的“转诊迹”应让评委形成以下印象：

> 这不是一个会替医生下判断的黑箱 AI，而是一套能在转院接诊前，把散乱材料快速整理为可核验时间轴、让医生立即回到原始证据并完成确认的可信工具。
