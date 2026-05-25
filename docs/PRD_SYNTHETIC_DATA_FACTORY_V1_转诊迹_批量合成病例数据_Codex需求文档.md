# 转诊迹 Synthetic Data Factory v1.0：批量合成病例数据生产与交付需求文档（Codex 执行版）

> **发送对象**：负责批量生成合成病例数据的队友及其 Codex  
> **对接项目**：`WangSibothunder/zgcHack` / 产品展示名“转诊迹｜转院病历证据时间轴”  
> **任务性质**：独立的数据生产分支，不与正在开发的前端、OCR/LLM 接入代码争抢修改范围  
> **目标**：为时间轴、现场拍摄/OCR、证据高亮和“证据联查”模块制造大量一致、可验证、可渲染为 PDF/图片的全合成病例数据  
> **仓库策略**：当前仓库保持 public；本任务产出的全部数据必须为虚构且显著标注 synthetic，不得含真实患者、真实病历或真实医院信息  
> **核心结论**：**JSON 结构化中间格式是唯一事实真源（source of truth）；PDF/PNG/JPG 仅为由其渲染得到的演示输入资产，不接受只交付 PDF 而没有 JSON 与 gold annotation 的数据集。**

---

# 0. 给 Codex 的开工指令

你负责的是“数据工厂”，不是主应用功能开发。开始前请阅读：

```text
README.md
AGENTS.md
demo-data/case-timeline.schema.json
demo-data/cases/demo-cardiac-transfer-001.json
docs/API_CONTRACT.md
docs/PRD_V0_8_ZHUANZHENJI.md                    # 若已合入
docs/PRD_V0_9_EVIDENCE_LINKED_SEARCH.md          # 若已合入
```

本任务必须在新分支执行：

```bash
git checkout -b feat/synthetic-data-factory-v1
```

除非为了增加数据 schema、生成脚本、校验脚本和文档，不要修改：

```text
demo-app/frontend/
demo-app/backend/
```

这样可以避免与主 Codex 正在开发的 v0.8/v0.9 功能冲突。

完成后你应交付：

1. 一套升级后的 canonical JSON Schema；
2. 可批量生成病例的脚本；
3. 可从 canonical JSON 渲染 PDF 与页面 PNG 的脚本；
4. 可生成 OCR gold bbox 与证据联查 expected hits 的标注文件；
5. 可生成模糊、反光、旋转、透视变形等采集端测试图片的脚本；
6. 首批经过自动校验的病例数据；
7. 数据统计报告和验收报告；
8. 提交到分支并发起 Pull Request，或将 commit hash 交给主开发者 cherry-pick。

---

# 1. 为什么不能只生成 PDF

你们的系统不是一个 PDF 浏览器，而是要验证以下功能：

```text
病历材料上传 / 摄像头拍摄
→ OCR 识别与文字坐标
→ 日期归并成时间轴
→ 字段原图证据高亮
→ 医生问题检索相关文档
→ 点击结果回到对应原文 bbox
```

若数据队友只交付 PDF，会出现这些问题：

| 只交付 PDF 的后果 | 对系统造成的影响 |
| --- | --- |
| 不知道正确 OCR 文本是什么 | 无法判断 OCR API 是否识别正确 |
| 不知道文字在图片中的坐标 | 无法验证证据高亮框是否正确 |
| 不知道哪些文档属于同一事件 | 时间轴聚合没有 ground truth |
| 不知道某个医生问题应该召回哪些片段 | “证据联查”没有测试标准答案 |
| 不知道哪些图片故意模糊/反光 | 质量检测无法自动验收 |
| 文档间事实可能相互矛盾 | 演示过程中出现病例逻辑错误 |

因此，本任务必须采用三层数据形态：

```text
Layer A：Canonical Structured Data（唯一真源，JSON）
    ↓ 确定性渲染
Layer B：Clinical Document Assets（PDF / PNG / JPG，模拟患者上传材料）
    ↓ OCR/检索/前端处理
Layer C：Gold Annotations & Expected Results（OCR bbox、证据命中、质量标签、查询答案）
```

**任何病例只有同时具备 A + B + C 三层，才算可交付病例。**

---

# 2. 与当前仓库的数据兼容策略

当前仓库 `demo-data/cases/*.json` 已经具有以下核心字段：

```text
synthetic
notice
case_id
patient
transfer
timeline_nodes
materials
```

并且时间节点中已有：

```text
node_id
date
materials
structured_fields
ocr_excerpt
evidence_anchors
```

本数据工厂不能破坏这些既有字段。应采取：

```text
保留旧版可读取字段
+ 新增 dataset_version、fact_graph、documents、pages、ocr_gold、segments、
  evidence_queries、quality_variants、generation_metadata
```

### 2.1 兼容原则

- 前端尚未读取的新字段可以先存入 JSON，不影响旧 Demo；
- 主开发 Codex 可逐步接入新字段；
- 原有 `timeline_nodes` 与 `materials` 必须继续可供 v1 API 读取；
- 新的 document/page/segment/evidence 查询结构将供 v2/v3 API 使用；
- 不直接将本数据格式强制实现为完整 FHIR；但字段命名应保持未来映射可能性：
  - `documents` 类似文档索引与元数据；
  - `document_type`、`authored_at`、`facility`、`department`、`content_asset` 应明确；
  - 检验/影像报告可额外带结构化 report fields。

---

# 3. 本任务的最终目录结构

请在仓库中新增独立目录，避免污染现有 `demo-data/`：

```text
synthetic-data-factory/
├─ README.md
├─ schemas/
│  ├─ transfer-case-bundle.v1.schema.json
│  ├─ document-page.v1.schema.json
│  ├─ ocr-gold.v1.schema.json
│  ├─ evidence-query-suite.v1.schema.json
│  └─ dataset-manifest.v1.schema.json
├─ configs/
│  ├─ dataset-plan.v1.yaml
│  ├─ fictional-facilities.yaml
│  ├─ document-types.yaml
│  ├─ retrieval-synonyms.yaml
│  └─ rendering-theme.yaml
├─ scripts/
│  ├─ generate_case_bundles.py
│  ├─ render_documents.py
│  ├─ build_ocr_gold.py
│  ├─ create_capture_variants.py
│  ├─ export_legacy_demo_cases.py
│  ├─ validate_dataset.py
│  └─ generate_dataset_report.py
├─ cases/
│  ├─ zj-card-001/
│  │  ├─ case_bundle.json
│  │  ├─ documents/
│  │  │  ├─ doc-card-001-emergency-note.json
│  │  │  └─ ...
│  │  ├─ rendered/
│  │  │  ├─ pdf/
│  │  │  ├─ pages_clean/
│  │  │  └─ pages_capture_variants/
│  │  ├─ annotations/
│  │  │  ├─ ocr_gold.json
│  │  │  ├─ evidence_queries.json
│  │  │  └─ quality_labels.json
│  │  └─ manifest.json
│  └─ ...
├─ dataset_manifest.json
└─ reports/
   ├─ DATASET_STATISTICS.md
   └─ DATASET_VALIDATION_REPORT.md
```

### 3.1 与应用仓库的交付路径

主开发应用如果不希望加载整个数据工厂，可由脚本导出一个轻量版本：

```text
demo-data/v2-export/
├─ cases/
├─ assets/
├─ annotations/
└─ index.json
```

导出必须通过：

```bash
python synthetic-data-factory/scripts/export_legacy_demo_cases.py \
  --input synthetic-data-factory/cases \
  --output demo-data/v2-export
```

不要人工复制文件，避免路径与 ID 不一致。

---

# 4. 数据生产路线：先事实图谱，再生成文档

## 4.1 禁止的生成方式

禁止让 LLM 或 Codex 对每份文档独立随意写作：

```text
生成 10 份门诊记录
再生成 10 份检验报告
再拼成患者病例
```

这种方法会导致：

- 日期冲突；
- 检验指标前后不一致；
- 转院原因与材料不对应；
- 同一个症状在不同文档中的时间顺序混乱；
- 证据联查无法建立可信 expected hits。

## 4.2 必须采用的生成方式

每位合成患者先生成一份 **Case Fact Graph（病例事实图谱）**，再由相同事实渲染不同文档：

```text
Case Fact Graph
├─ 虚构患者与转院路径
├─ 时间事件序列
├─ 每个事件涉及的事实 fact_id
├─ 哪些材料记载了哪些 fact_id
├─ 哪些事实与转院原因相关
├─ 哪些问题应该检索到哪些 fact_id
└─ 哪些材料故意缺失或待补充
        ↓
Document Generator
        ↓
PDF / Page Images / OCR Gold / Query Gold
```

### 4.3 Fact 的定义

`fact` 不是系统诊断结论，而是**材料中应出现的原文记载单元**。

允许的 fact 示例：

```json
{
  "fact_id": "fact-card-001-symptom-chest-discomfort-01",
  "fact_type": "documented_symptom",
  "canonical_label": "胸部不适",
  "display_text": "记录中提到胸部不适持续约 2 小时。",
  "source_style": "explicit_record",
  "related_to_transfer_reason": true
}
```

```json
{
  "fact_id": "fact-appetite-001-loss-02",
  "fact_type": "documented_symptom",
  "canonical_label": "食欲欠佳",
  "display_text": "记录中写有“近一周食欲欠佳，进食量较前减少”。",
  "retrieval_aliases": ["食欲不振", "纳差", "进食减少"],
  "related_to_transfer_reason": false
}
```

不允许的 fact 示例：

```json
{
  "fact_type": "system_diagnosis",
  "display_text": "患者患有某疾病并需要治疗"
}
```

本数据集只制造“病历原文中写了什么”的证据，不制造系统新诊断或治疗推荐。

---

# 5. 数据规模与批次计划

黑客松阶段不要盲目生成数千份无法检查的数据。采用三阶段交付：

## Batch A：接口锁定集（必须先完成）

目标：验证 schema、渲染、OCR 高亮、证据联查和质量检测均可接入。

| 指标 | 数量 |
| --- | ---: |
| 合成患者病例 | 6 |
| 科室/转院方向 | 3 类 |
| 每病例时间节点 | 5–8 |
| 每病例文档 | 8–12 |
| 总文档数 | 约 60 |
| 每文档页数 | 1–2 |
| 可检索问题 | 每病例 6 条 |
| 每病例质量退化图片 | 至少 4 张 |

建议病例类型：

| case_id 前缀 | 场景 | 证据联查重点 |
| --- | --- | --- |
| `zj-card-*` | 心内科转院材料 | 胸部不适、既往标记字段、转院文字 |
| `zj-digest-*` | 消化/内科转院材料 | 食欲欠佳、纳差、进食减少等同义召回 |
| `zj-neuro-*` | 神经内科转院材料 | 既往症状描述、影像报告文字定位 |

## Batch B：路演丰富集（Batch A 校验通过后）

| 指标 | 数量 |
| --- | ---: |
| 合成病例总数 | 20 |
| 文档总数 | 180–240 |
| 科室/场景类型 | 5 |
| 每病例查询问题 | 8–12 |
| 每病例干扰文档 | 至少 2 |

可增加：

- 肿瘤随访/转入材料整理；
- 呼吸内科转院材料；
- 内分泌相关复诊与转院材料。

## Batch C：压力与统计集（时间允许再做）

| 指标 | 数量 |
| --- | ---: |
| 合成病例总数 | 50 |
| 文档总数 | 500+ |
| 用途 | 检索延迟测试、页面列表压力、统计演示 |

**Codex 不得跳过 Batch A 验证直接生成 Batch C。**

---

# 6. Canonical Case Bundle JSON 规范

每位患者必须有 `case_bundle.json`，这是唯一事实真源。

## 6.1 顶层字段

```json
{
  "schema_version": "transfer-case-bundle.v1",
  "dataset_version": "synthetic-factory-v1.0",
  "synthetic": true,
  "synthetic_notice": "合成演示材料 / SYNTHETIC DEMO DOCUMENT / 不对应真实患者，不构成诊断或治疗建议。",
  "case_id": "zj-digest-001",
  "case_seed": 1001,
  "scenario_type": "transfer_record_reconstruction",
  "patient": {},
  "transfer": {},
  "fact_graph": {},
  "timeline_nodes": [],
  "documents": [],
  "materials": {},
  "evidence_query_suite_path": "annotations/evidence_queries.json",
  "generation_metadata": {}
}
```

### 强制约束

- `synthetic` 必须恒为 `true`；
- `case_id` 必须全数据集唯一；
- `case_seed` 必须存在，以支持重复渲染；
- `synthetic_notice` 必须出现在 JSON 和所有渲染文档第一页中；
- `documents` 中每份文档必须关联一个 `timeline_node`；
- `timeline_nodes` 必须按日期升序；
- 一个文档可关联多个 fact，但不得引用不存在的 `fact_id`；
- 所有 evidence anchor 必须可追溯到 document/page/ocr block/bbox。

---

## 6.2 patient 字段

使用完全虚构且带演示标识的信息：

```json
{
  "display_name": "演示患者 D01",
  "sex": "女",
  "age_display": "56 岁",
  "patient_demo_id": "SYN-D01",
  "fictional": true
}
```

禁止生成：

- 真实姓名形式，如常见完整姓名；
- 身份证号、手机号、家庭住址；
- 可对应真实机构的住院号；
- 真实照片或人脸图像。

---

## 6.3 transfer 字段

```json
{
  "origin_hospital": "青禾县中心医院（虚构）",
  "destination_hospital": "澄明医学中心（虚构）",
  "destination_department": "消化内科",
  "reason_recorded": "外院记录记载症状反复，建议到上级机构进一步评估。",
  "coverage_start": "2025-01-02",
  "coverage_end": "2025-01-20",
  "missing_material_reminders": [
    {
      "reminder_id": "miss-digest-001-01",
      "text": "当前材料中未发现某次检查的完整报告，请人工核对是否需要补充。",
      "category": "document_completeness_only"
    }
  ]
}
```

禁止写：

```text
患者必须接受某检查
患者应接受某治疗
患者属于高风险
```

---

## 6.4 fact_graph 字段

```json
{
  "facts": [
    {
      "fact_id": "fact-digest-001-appetite-01",
      "fact_type": "documented_symptom",
      "canonical_label": "食欲欠佳",
      "document_wording_variants": [
        "食欲欠佳",
        "纳差",
        "进食量较前减少"
      ],
      "related_to_transfer_reason": false,
      "permitted_summary": "材料中存在关于食欲欠佳或进食量减少的记载。"
    },
    {
      "fact_id": "fact-digest-001-transfer-01",
      "fact_type": "documented_transfer_note",
      "canonical_label": "建议到上级机构进一步评估",
      "document_wording_variants": [
        "建议转上级医院进一步评估",
        "建议至上级机构继续诊治"
      ],
      "related_to_transfer_reason": true,
      "permitted_summary": "材料原文记载了前往上级机构进一步评估的建议。"
    }
  ],
  "consistency_rules": [
    {
      "rule_id": "rule-digest-001-sequence",
      "description": "转院相关记载出现时间不得早于首次相关就诊记录。",
      "assertion": "fact-digest-001-transfer-01.date >= first_visit.date"
    }
  ]
}
```

### fact_type 枚举

P0 只允许：

```text
documented_symptom
documented_measurement
documented_abnormal_marker
documented_exam_text
documented_medication_record
documented_hospitalization
documented_discharge_note
documented_transfer_note
document_completeness_reminder
```

任何形式的 `system_diagnosis`、`treatment_recommendation`、`risk_prediction` 禁止出现。

---

## 6.5 timeline_nodes 字段

兼容现有前端的同时扩展：

```json
{
  "node_id": "node-digest-20250109",
  "date": "2025-01-09",
  "hospital_department": "青禾县中心医院（虚构）｜消化内科",
  "document_type": "门诊病历 + 检验报告",
  "headline": "门诊随访材料",
  "summary": "该日期材料记录了症状描述与待核验字段。",
  "tags": [
    {"label": "症状记录", "level": "info"},
    {"label": "待核验", "level": "warning"}
  ],
  "related_to_transfer_reason": false,
  "has_abnormal_flag": false,
  "materials": [
    "mat-digest-20250109-visit",
    "mat-digest-20250109-lab"
  ],
  "fact_ids": [
    "fact-digest-001-appetite-01"
  ],
  "structured_fields": {
    "材料类型": "门诊病历 + 检验报告",
    "原文相关记录": "食欲欠佳，进食量较前减少"
  },
  "ocr_excerpt": "合成演示材料｜患者近一周食欲欠佳，进食量较前减少。",
  "evidence_anchors": [
    {
      "anchor_id": "ev-digest-appetite-20250109",
      "material_id": "mat-digest-20250109-visit",
      "page_id": "page-digest-20250109-visit-01",
      "fact_id": "fact-digest-001-appetite-01",
      "field_key": "原文相关记录",
      "display_value": "食欲欠佳，进食量较前减少",
      "locator_text": "食欲欠佳，进食量较前减少",
      "ocr_block_ids": ["ocr-digest-20250109-visit-b04"],
      "bbox": [92, 312, 684, 352],
      "confidence": 1.0,
      "verification_status": "unreviewed",
      "is_abnormal_flag": false
    }
  ]
}
```

注意：

- `confidence: 1.0` 在 gold annotation 中代表生成时真值坐标；运行 OCR 后的预测置信度应另存，不覆盖 gold；
- 前端展示 OCR API 预测时，应使用预测字段；测试对比时用 gold；
- `summary` 只说明材料中记录了什么，不写新的医学判断。

---

# 7. 文档级数据规范

每份模拟病历材料必须在 canonical JSON 中作为 `document` 存在，并渲染为 PDF 与 PNG 页面。

## 7.1 documents 字段

```json
{
  "document_id": "doc-digest-20250109-visit",
  "material_id": "mat-digest-20250109-visit",
  "node_id": "node-digest-20250109",
  "document_type": "outpatient_note",
  "document_type_display": "门诊病历",
  "authored_at": "2025-01-09",
  "facility": "青禾县中心医院（虚构）",
  "department": "消化内科",
  "author_display": "记录医师：演示医师 02（虚构）",
  "page_count": 1,
  "fact_ids": ["fact-digest-001-appetite-01"],
  "render_template": "outpatient_note_a4_v1",
  "content_blocks": [
    {
      "block_id": "block-header",
      "block_type": "header",
      "text": "青禾县中心医院（虚构） 门诊病历"
    },
    {
      "block_id": "block-synthetic-watermark",
      "block_type": "watermark",
      "text": "合成演示材料 / SYNTHETIC DEMO DOCUMENT / 不对应真实患者"
    },
    {
      "block_id": "block-chief-complaint",
      "block_type": "record_text",
      "text": "记录：患者近一周食欲欠佳，进食量较前减少。",
      "fact_ids": ["fact-digest-001-appetite-01"],
      "requires_evidence_anchor": true
    }
  ],
  "assets": {
    "pdf_path": "rendered/pdf/doc-digest-20250109-visit.pdf",
    "clean_page_paths": [
      "rendered/pages_clean/doc-digest-20250109-visit-p01.png"
    ]
  }
}
```

## 7.2 document_type 枚举

P0 生成以下文档即可：

| 枚举值 | 中文显示 | 用途 |
| --- | --- | --- |
| `outpatient_note` | 门诊病历 | 主诉、复查记录、转诊原文 |
| `emergency_note` | 急诊病历 | 初次就诊材料 |
| `admission_note` | 入院记录 | 住院过程起点 |
| `discharge_summary` | 出院小结 | 既往诊疗过程与转院文字 |
| `laboratory_report` | 检验报告 | 带数值/标记字段 |
| `imaging_report` | 影像报告 | 影像文字描述 |
| `ecg_report` | 心电图报告 | 心内科场景材料 |
| `medication_record` | 用药记录 | 仅展示材料存在与药物记录，不做建议 |

---

# 8. PDF 与图片资产要求

## 8.1 PDF 不是手写产物，而是脚本渲染产物

从 `document.content_blocks` 确定性渲染：

```bash
python synthetic-data-factory/scripts/render_documents.py \
  --cases synthetic-data-factory/cases \
  --format pdf,png \
  --overwrite
```

渲染脚本建议使用以下之一：

- Python ReportLab：便于生成 A4 PDF 与控制文字位置；
- HTML/CSS 模板 + Playwright 截图/PDF：视觉较好，需固定字体与 viewport。

选择一种即可，但必须满足：

- 相同 JSON + 相同 seed 重复运行输出文本与坐标一致；
- 每份文档第一页顶部或水印显著显示 synthetic 提示；
- 使用虚构医院与虚构患者编号；
- 输出干净页面 PNG，供 OCR 与高亮测试；
- 输出 PDF，供文件上传与路演展示。

## 8.2 渲染样式

每份文档必须肉眼像真实“材料类型”，但不可假冒真实机构文件：

- 标题采用虚构机构名；
- 右上或底部固定水印；
- 用 `演示患者 XX` 而不是普通真实姓名；
- 可包含表格、字段、日期、页码；
- 禁止出现真实医院 Logo、印章、二维码、真实医生签名、真实联系电话。

## 8.3 PDF/图片命名规范

```text
{case_id}__{document_id}__clean.pdf
{case_id}__{document_id}__p01__clean.png
{case_id}__{document_id}__p01__blur-moderate.png
{case_id}__{document_id}__p01__glare-keyfield.png
{case_id}__{document_id}__p01__rotate-8deg.png
{case_id}__{document_id}__p01__perspective-light.png
```

---

# 9. OCR Gold Annotation 规范

本数据集的巨大价值在于：文档是自己渲染的，因此可以直接获得“正确文本 + 正确坐标”，用于测 OCR API 和证据高亮。

## 9.1 每页必须产生的 OCR gold

`annotations/ocr_gold.json`：

```json
{
  "schema_version": "ocr-gold.v1",
  "case_id": "zj-digest-001",
  "pages": [
    {
      "page_id": "page-digest-20250109-visit-01",
      "document_id": "doc-digest-20250109-visit",
      "image_path": "rendered/pages_clean/doc-digest-20250109-visit-p01.png",
      "width": 1240,
      "height": 1754,
      "blocks": [
        {
          "ocr_block_id": "ocr-digest-20250109-visit-b04",
          "block_type": "record_text",
          "text": "记录：患者近一周食欲欠佳，进食量较前减少。",
          "bbox": [92, 312, 684, 352],
          "polygon": [[92,312],[684,312],[684,352],[92,352]],
          "fact_ids": ["fact-digest-001-appetite-01"],
          "is_evidence_target": true
        }
      ]
    }
  ]
}
```

### 9.2 bbox 规则

统一坐标格式：

```text
[x_min, y_min, x_max, y_max]
```

要求：

- 坐标基于 `pages_clean/*.png` 的像素尺寸；
- 坐标必须由渲染器生成，不允许人工大批量估测；
- `polygon` 可选保留，便于未来兼容 OCR API 四点坐标；
- OCR API 实际输出是 prediction，保存在 runtime，不提交为 gold 覆盖原文件。

### 9.3 OCR 评估可选输出

若主开发已接入外部 OCR API，数据工厂可提供一个离线评估脚本：

```bash
python synthetic-data-factory/scripts/evaluate_ocr_predictions.py \
  --gold synthetic-data-factory/cases \
  --pred runtime/ocr_predictions \
  --output reports/OCR_EVALUATION_REPORT.md
```

报告至少统计：

- 页面识别成功率；
- 关键字段字符串是否被识别；
- 关键 bbox 是否可映射；
- clean 与 degraded 样例的差异。

不要求在本数据任务中调用真实 API，重点是提供可测数据。

---

# 10. 证据联查 Query Suite 规范

证据联查模块要求“医生提出问题 → 系统返回相关文档与原文”。因此数据队友必须交付标准问题与期望命中。

## 10.1 每病例至少包含的问题类型

| 类型 | 示例 | 预期 |
| --- | --- | --- |
| 直接提及查询 | “材料中是否提到食欲欠佳？” | 命中包含原词的片段 |
| 同义表述查询 | “是否记录过食欲不振？” | 可命中“纳差”“食欲欠佳” |
| 时间查询 | “最近一次提到胸部不适是什么时间？” | 命中最后一个明确记录节点 |
| 转院原因查询 | “哪份材料写过建议转上级机构？” | 命中转院相关记录 |
| 重复字段查询 | “哪些材料出现过肌钙蛋白字段？” | 命中对应检验片段 |
| 无结果安全查询 | “是否提到某个未出现症状？” | 返回空，并有安全文案 |
| 干扰排除查询 | 查询症状但有无关检查报告 | 不应召回无关文档 |
| 选中文字关联 | 以某一 segment 触发 related records | 返回其他相关日期，不返回当前片段自身 |

## 10.2 evidence_queries.json 格式

```json
{
  "schema_version": "evidence-query-suite.v1",
  "case_id": "zj-digest-001",
  "synthetic": true,
  "queries": [
    {
      "query_id": "query-digest-appetite-synonym-01",
      "trigger_type": "question",
      "question": "病人最近的材料中是否提到食欲不振？",
      "retrieval_concepts": ["食欲不振"],
      "allowed_expanded_terms": ["食欲欠佳", "纳差", "进食减少", "进食量较前减少"],
      "expected_hits": [
        {
          "segment_id": "seg-digest-20250109-visit-appetite",
          "relevance_level": "synonymous_mention",
          "required": true,
          "acceptable_summary": "该记录明确提到食欲欠佳及进食量减少。"
        },
        {
          "segment_id": "seg-digest-20250112-admission-appetite",
          "relevance_level": "direct_mention",
          "required": true,
          "acceptable_summary": "该记录包含食欲不振的文字记载。"
        }
      ],
      "forbidden_hits": [
        "seg-digest-20250114-imaging-unrelated"
      ],
      "safe_result_statement": "在当前合成材料中找到与食欲相关的明确记录。",
      "must_not_generate": [
        "患者确实存在食欲不振",
        "病因判断",
        "治疗建议",
        "检查建议"
      ]
    }
  ]
}
```

### 10.3 DocumentSegment 输出

数据工厂必须从页面内容块与 OCR gold 中自动建立 segment：

```json
{
  "segment_id": "seg-digest-20250109-visit-appetite",
  "case_id": "zj-digest-001",
  "node_id": "node-digest-20250109",
  "material_id": "mat-digest-20250109-visit",
  "document_id": "doc-digest-20250109-visit",
  "page_id": "page-digest-20250109-visit-01",
  "document_date": "2025-01-09",
  "document_type": "门诊病历",
  "department": "消化内科",
  "raw_text": "记录：患者近一周食欲欠佳，进食量较前减少。",
  "normalized_terms": ["食欲欠佳", "进食量减少"],
  "fact_ids": ["fact-digest-001-appetite-01"],
  "ocr_block_ids": ["ocr-digest-20250109-visit-b04"],
  "bboxes": [[92, 312, 684, 352]],
  "synthetic": true
}
```

---

# 11. 拍摄与质量检测退化样本

为了演示“商业摄像机/手机采集端”与图片质量反馈，每个 Batch A 病例至少选择一张关键材料生成退化版本。

## 11.1 必做退化类型

| 变体 | 目的 | Gold label |
| --- | --- | --- |
| clean | 正常通过 OCR 与证据定位 | `pass` |
| blur_moderate | 演示模糊重拍提示 | `retake_required` |
| glare_keyfield | 高光遮挡关键字段 | `retake_required` 或严格 `warning` |
| rotate_light | 轻微旋转，测试矫正能力 | `processable_with_warning` |
| perspective_light | 轻度斜拍 | `processable_with_warning` |
| crop_missing_corner | 页面缺角，影响日期或字段 | `retake_required` |

## 11.2 quality_labels.json

```json
{
  "schema_version": "quality-labels.v1",
  "case_id": "zj-digest-001",
  "variants": [
    {
      "variant_id": "quality-digest-lab-clean",
      "source_page_id": "page-digest-20250109-visit-01",
      "image_path": "rendered/pages_clean/doc-digest-20250109-visit-p01.png",
      "degradation_type": "none",
      "expected_quality_status": "pass",
      "key_evidence_visible": true
    },
    {
      "variant_id": "quality-digest-lab-glare",
      "source_page_id": "page-digest-20250109-visit-01",
      "image_path": "rendered/pages_capture_variants/doc-digest-20250109-visit-p01__glare-keyfield.png",
      "degradation_type": "glare_keyfield",
      "expected_quality_status": "retake_required",
      "key_evidence_visible": false,
      "affected_ocr_block_ids": ["ocr-digest-20250109-visit-b04"]
    }
  ]
}
```

## 11.3 生成方式

使用 Pillow / OpenCV 编程生成退化版本，必须保留生成参数：

```json
{
  "degradation_seed": 100102,
  "parameters": {
    "gaussian_blur_radius": 5,
    "glare_polygon": [[90,300],[700,300],[700,372],[90,372]],
    "glare_opacity": 0.82
  }
}
```

这样主开发可以复现质量检测 bug，而不是依赖人工制作的不可复现图片。

---

# 12. 虚构内容生成安全与质量规则

## 12.1 所有病例必须显著为虚构

必须使用：

```text
患者：演示患者 A01 / D01 / N01
医院：青禾县中心医院（虚构）、澄明医学中心（虚构）、云川医学中心（虚构）
页眉/水印：合成演示材料 / SYNTHETIC DEMO DOCUMENT / 不对应真实患者
```

禁止使用：

- 真实医院全称；
- 真实 Logo；
- 真实医生签名；
- 真实电话号码、住址或二维码；
- 来自网络真实病历的改写或截图；
- 任何真实患者 OCR 内容。

## 12.2 医疗文本表达边界

合成文档可以模拟“既往材料原文”中的描述，以验证系统检索能力，例如：

```text
记录：患者近一周食欲欠佳，进食量较前减少。
记录：建议前往上级机构进一步评估。
检验报告：某字段出现标记，待接诊人员结合原始材料核验。
```

数据集的系统概要只能写：

```text
材料中存在该文字记载。
该字段来自指定合成文档与指定区域。
当前材料中未发现某类文档，请人工核对是否需要补充。
```

禁止将系统概要写成：

```text
患者已确诊为……
患者需要……
建议进行某治疗……
该情况由某病因造成……
```

## 12.3 文档一致性要求

每个病例必须自动检查：

- 转院日期晚于或等于已有材料最后日期；
- `coverage_start` / `coverage_end` 覆盖所有时间节点；
- 每个 node 引用的 material 存在；
- 每个 material 引用的 document、page 和渲染资产存在；
- 每个 anchor 引用的 fact、OCR block 与 bbox 存在；
- 每个 query expected hit 的 segment 存在；
- forbidden hit 不同时出现在 expected hits；
- 同一合成患者的年龄/性别/转院路径不在文档中自相矛盾；
- 文档中的医院均位于 fictional facility 配置表中；
- 所有 PDF/PNG 页面包含 synthetic 水印。

---

# 13. 配置驱动生成而不是硬编码

## 13.1 fictional-facilities.yaml

```yaml
facilities:
  - id: facility-qinghe-county
    display_name: 青禾县中心医院（虚构）
    level_label: 基层转出机构（演示）
    departments: [急诊科, 心内科, 消化内科, 神经内科, 呼吸内科]
  - id: facility-chengming-center
    display_name: 澄明医学中心（虚构）
    level_label: 上级接收机构（演示）
    departments: [心内科, 消化内科, 神经内科, 肿瘤科]
```

## 13.2 retrieval-synonyms.yaml

只用于检索测试，不用于诊断推理：

```yaml
concepts:
  appetite_reduction:
    display: 食欲不振
    terms: [食欲不振, 食欲欠佳, 纳差, 进食减少, 进食量较前减少]
  chest_discomfort:
    display: 胸部不适
    terms: [胸部不适, 胸前区不适, 胸痛]
  transfer_reference:
    display: 转院相关记载
    terms: [转院, 转诊, 转上级医院, 上级机构进一步评估]
  troponin_text:
    display: 肌钙蛋白文字字段
    terms: [肌钙蛋白, 肌钙蛋白 I, cTnI, TnI]
```

## 13.3 dataset-plan.v1.yaml

```yaml
dataset_version: synthetic-factory-v1.0
batch: A
case_count: 6
seed: 20260525
cases:
  - case_id: zj-card-001
    specialty: cardiology
    node_count: 6
    document_count: 10
    query_concepts: [chest_discomfort, transfer_reference, troponin_text]
  - case_id: zj-card-002
    specialty: cardiology
    node_count: 5
    document_count: 8
    query_concepts: [chest_discomfort, transfer_reference]
  - case_id: zj-digest-001
    specialty: gastroenterology
    node_count: 6
    document_count: 10
    query_concepts: [appetite_reduction, transfer_reference]
  - case_id: zj-digest-002
    specialty: gastroenterology
    node_count: 5
    document_count: 8
    query_concepts: [appetite_reduction]
  - case_id: zj-neuro-001
    specialty: neurology
    node_count: 6
    document_count: 10
    query_concepts: [transfer_reference]
  - case_id: zj-neuro-002
    specialty: neurology
    node_count: 5
    document_count: 8
    query_concepts: [transfer_reference]
```

---

# 14. 生成脚本要求

## 14.1 generate_case_bundles.py

职责：

- 读取 dataset plan、虚构机构配置、同义词配置；
- 按 seed 构造一致的 fact graph；
- 生成 canonical `case_bundle.json` 与 document JSON；
- 生成 query expected hits 定义；
- 不直接生成 PDF。

命令：

```bash
python synthetic-data-factory/scripts/generate_case_bundles.py \
  --config synthetic-data-factory/configs/dataset-plan.v1.yaml \
  --output synthetic-data-factory/cases \
  --overwrite
```

## 14.2 render_documents.py

职责：

- 从 document JSON 渲染 PDF 与干净页面 PNG；
- 在渲染阶段同步产生文字块 bbox；
- 每页加入 synthetic 水印；
- 输出渲染 manifest。

命令：

```bash
python synthetic-data-factory/scripts/render_documents.py \
  --cases synthetic-data-factory/cases \
  --output-format pdf,png \
  --overwrite
```

## 14.3 build_ocr_gold.py

职责：

- 读取渲染输出中的文字布局坐标；
- 写出 `ocr_gold.json`；
- 写出 `DocumentSegment`；
- 校验 evidence anchor 是否能指向 page 和 bbox。

## 14.4 create_capture_variants.py

职责：

- 从 clean PNG 生成 blur / glare / rotate / perspective / crop 版本；
- 写出质量标签与参数；
- 只对关键页面或配置指定页面生成退化版本，避免仓库体积爆炸。

## 14.5 validate_dataset.py

职责：

- JSON Schema 验证；
- 路径与 ID 引用完整性验证；
- 时间顺序与事实一致性验证；
- 水印存在性验证；
- bbox 坐标边界验证；
- query expected hit 与 segment 对应验证；
- public 数据安全关键词扫描；
- 生成 machine-readable 验证结果。

命令：

```bash
python synthetic-data-factory/scripts/validate_dataset.py \
  --dataset synthetic-data-factory \
  --report synthetic-data-factory/reports/DATASET_VALIDATION_REPORT.md
```

### 必须失败的条件

发现以下任一情况，脚本退出码必须非零：

- `synthetic` 非 `true`；
- 未包含 synthetic notice；
- 日期/引用/路径不一致；
- evidence anchor 无 bbox 或无 segment（用于新数据时）；
- query required hit 不存在；
- 页面缺少水印；
- 出现疑似真实手机号、身份证号、真实医院白名单外机构；
- 渲染文件缺失；
- case_id、document_id、page_id、anchor_id、segment_id 重复。

## 14.6 generate_dataset_report.py

生成：

```text
reports/DATASET_STATISTICS.md
reports/DATASET_VALIDATION_REPORT.md
```

统计至少包括：

- 病例数；
- 各科室病例数；
- 节点总数与分布；
- 文档总数与文档类型分布；
- 页数；
- evidence anchor 数；
- segment 数；
- query 数与 direct/synonym/no-result 类型数量；
- clean 与 degraded 图片数；
- 验证通过/失败项；
- 数据全部 synthetic 的声明。

---

# 15. 数据集 Manifest

数据集根目录必须有 `dataset_manifest.json`：

```json
{
  "schema_version": "dataset-manifest.v1",
  "dataset_name": "ZhuanZhenJi Synthetic Transfer Document Dataset",
  "dataset_version": "synthetic-factory-v1.0-batchA",
  "synthetic": true,
  "public_repository_safe": true,
  "notice": "全部内容为合成演示数据，不对应真实患者，不得用于临床判断。",
  "generated_at": "2026-05-25",
  "generator_commit": "<fill-after-commit>",
  "case_ids": [
    "zj-card-001",
    "zj-card-002",
    "zj-digest-001",
    "zj-digest-002",
    "zj-neuro-001",
    "zj-neuro-002"
  ],
  "counts": {
    "cases": 6,
    "documents": 0,
    "pages_clean": 0,
    "pages_degraded": 0,
    "anchors": 0,
    "segments": 0,
    "queries": 0
  },
  "validation": {
    "schema_validated": false,
    "reference_integrity_validated": false,
    "synthetic_watermark_validated": false,
    "public_safety_scan_validated": false
  }
}
```

脚本在生成与验证后自动填写 `counts` 与 `validation`，不要人工随意改统计数。

---

# 16. 兼容主应用的最小导出格式

主开发不应在 v0.8/v0.9 中立即理解数据工厂全部字段。为了快速接入，提供 `export_legacy_demo_cases.py`，输出当前应用能读取的简化格式。

导出字段至少包含：

```json
{
  "synthetic": true,
  "notice": "合成演示数据，仅用于材料整理演示，不构成诊断或治疗建议。",
  "case_id": "zj-digest-001",
  "patient": {},
  "transfer": {},
  "timeline_nodes": [
    {
      "node_id": "node-digest-20250109",
      "date": "2025-01-09",
      "hospital_department": "...",
      "document_type": "...",
      "headline": "...",
      "summary": "...",
      "tags": [],
      "related_to_transfer_reason": false,
      "has_abnormal_flag": false,
      "materials": [],
      "structured_fields": {},
      "ocr_excerpt": "...",
      "evidence_anchors": []
    }
  ],
  "materials": {}
}
```

新增 v3 证据联查接口读取扩展目录：

```text
demo-data/v2-export/annotations/segments.json
demo-data/v2-export/annotations/evidence_queries.json
demo-data/v2-export/assets/
```

---

# 17. 测试要求

## 17.1 单元测试

必须新增：

```text
tests/test_generate_case_bundles.py
tests/test_render_documents.py
tests/test_build_ocr_gold.py
tests/test_quality_variants.py
tests/test_validate_dataset.py
tests/test_legacy_export.py
```

测试必须覆盖：

- 相同 seed 重复生成相同 ID、日期与文字；
- 每个新病例均有 synthetic notice；
- 每个文档都能渲染 PDF 与 clean PNG；
- 每个 evidence anchor 都有合法 bbox；
- bbox 不超出图片尺寸；
- 每个 query required hit 存在且指向正确 segment；
- 食欲不振问题能以 gold 命中“食欲欠佳”“纳差”片段；
- 无结果查询不包含 expected hit；
- glare/blur 等退化图片有对应 label；
- legacy export 可以被现有 v1 API 所需字段读取；
- 安全扫描能拒绝去水印样例或疑似敏感数据样例。

## 17.2 验收命令

Codex 必须在提交前实际运行：

```bash
python -m pytest synthetic-data-factory/tests -q

python synthetic-data-factory/scripts/generate_case_bundles.py \
  --config synthetic-data-factory/configs/dataset-plan.v1.yaml \
  --output synthetic-data-factory/cases \
  --overwrite

python synthetic-data-factory/scripts/render_documents.py \
  --cases synthetic-data-factory/cases \
  --output-format pdf,png \
  --overwrite

python synthetic-data-factory/scripts/build_ocr_gold.py \
  --cases synthetic-data-factory/cases

python synthetic-data-factory/scripts/create_capture_variants.py \
  --cases synthetic-data-factory/cases

python synthetic-data-factory/scripts/validate_dataset.py \
  --dataset synthetic-data-factory \
  --report synthetic-data-factory/reports/DATASET_VALIDATION_REPORT.md

python synthetic-data-factory/scripts/export_legacy_demo_cases.py \
  --input synthetic-data-factory/cases \
  --output demo-data/v2-export

python synthetic-data-factory/scripts/generate_dataset_report.py \
  --dataset synthetic-data-factory \
  --output synthetic-data-factory/reports/DATASET_STATISTICS.md
```

完成报告必须粘贴真实命令与真实退出结果，不得先写“通过”再补跑。

---

# 18. public 仓库安全检查

## 18.1 禁止提交的内容

```text
.env
API key / token / secret
runtime/ 上传文件
真实患者材料
来自真实医院的报告截图
真实医生签名/印章/二维码/联系电话
外部 OCR/LLM 的含真实材料响应缓存
数据库运行文件
```

## 18.2 提交前检查命令

```bash
git status --short

git ls-files | grep -Ei '(\.env|runtime|sqlite|\.db|token|secret|credential)' && exit 1 || true

grep -RInE '([0-9]{17}[0-9Xx]|1[3-9][0-9]{9})' synthetic-data-factory/cases demo-data/v2-export \
  && echo "发现疑似身份证号或手机号，禁止提交" && exit 1 || true

python synthetic-data-factory/scripts/validate_dataset.py \
  --dataset synthetic-data-factory \
  --report synthetic-data-factory/reports/DATASET_VALIDATION_REPORT.md
```

### 18.3 真实数据绝对隔离

若团队后续需要测试真实材料：

- 不得放在此 public 仓库；
- 不得发送给本数据生成 Codex；
- 不得调用免费外部 API 处理；
- 必须迁移至独立合规环境后另行评审。

---

# 19. 数据质量标准（Definition of Done）

## Batch A 交付必须满足

- [ ] 建立 `synthetic-data-factory/` 独立目录；
- [ ] 建立 canonical schema 与数据 manifest；
- [ ] 生成 6 个合成病例，覆盖心内科、消化/内科、神经内科三类场景；
- [ ] 每病例 5–8 个时间节点；
- [ ] 总文档数约 60，且每份文档有 PDF 与 clean PNG；
- [ ] 所有文档页面可见 synthetic 水印；
- [ ] 每病例包含事实图谱，文档由事实图谱渲染而来；
- [ ] 每个关键字段具有 OCR gold text 与 bbox；
- [ ] 每病例至少 6 条 evidence query expected results；
- [ ] 至少包含“食欲不振 / 食欲欠佳 / 纳差 / 进食减少”同义检索测试病例；
- [ ] 每病例至少一个页面产生 clean + blur + glare + rotate/perspective 采集变体；
- [ ] 所有 ID、引用、路径、bbox、query hits 通过校验；
- [ ] 可导出到当前应用兼容的 `demo-data/v2-export/`；
- [ ] 报告包含实际统计结果；
- [ ] 数据仓库安全扫描通过；
- [ ] 只修改数据、schema、脚本和文档，不破坏主应用代码。

---

# 20. 对接主开发 Codex 的交付说明模板

完成 Batch A 后，向负责前后端的同学发送以下内容：

```text
Synthetic Data Factory Batch A 已完成。

交付路径：
- canonical 数据：synthetic-data-factory/cases/
- schema：synthetic-data-factory/schemas/
- 兼容当前时间轴的导出数据：demo-data/v2-export/
- PDF/图片资产：synthetic-data-factory/cases/*/rendered/
- OCR gold 与 bbox：synthetic-data-factory/cases/*/annotations/ocr_gold.json
- 证据联查标准问题：synthetic-data-factory/cases/*/annotations/evidence_queries.json
- 数据报告：synthetic-data-factory/reports/

接入建议：
1. 当前 v1 时间轴继续读取 demo-data/v2-export/cases；
2. v2 OCR/证据高亮可读取 clean/capture assets 与 ocr_gold 作为 fallback/测试 gold；
3. v3 证据联查读取 segments 与 evidence_queries 做 E2E 验收；
4. 不要在 UI 中将 gold annotation 伪称为外部 OCR API 的真实预测；
5. 若外部 OCR/LLM 接入成功，应另存 prediction/runtime 结果并与 gold 对照。

验证命令与结果已记录在 DATASET_VALIDATION_REPORT.md。
```

---

# 21. Codex 最终任务消息（直接复制）

```text
你负责为“转诊迹｜转院病历证据时间轴”生产可批量扩展的全合成病例数据。
请读取仓库现有 README、AGENTS.md、demo-data/case-timeline.schema.json、
demo-data/cases/demo-cardiac-transfer-001.json、docs/API_CONTRACT.md，以及本文件
docs/PRD_SYNTHETIC_DATA_FACTORY_V1.md。

请在新分支 `feat/synthetic-data-factory-v1` 完成工作，尽量不要修改正在由其他
Codex 改造的 demo-app/frontend 与 demo-app/backend。

最重要的架构决策：
- JSON canonical case bundle 是唯一事实真源；
- PDF/PNG/JPG 是由 JSON 确定性渲染得到的上传/摄像头演示资产；
- OCR gold bbox、DocumentSegment、证据联查 query expected hits 和质量退化标签
  都必须由 canonical 数据同步生成；
- 不接受仅生成很多 PDF 却没有结构化真值和验收数据的交付。

先完成 Batch A，不要盲目扩大数据规模：
- 6 个合成转院病例；
- 覆盖心内科、消化/内科、神经内科；
- 每病例 5–8 个节点、8–12 份文档，总计约 60 份文档；
- 生成 PDF 与 clean PNG；
- 关键字段 OCR gold + bbox；
- 每病例至少 6 条证据联查标准问题；
- 重点包含能测试“食欲不振 / 食欲欠佳 / 纳差 / 进食减少”相关召回的病例；
- 每病例至少一张关键页具有 blur、glare、rotate/perspective 等采集退化变体；
- 可导出为当前应用可读取的 demo-data/v2-export 轻量格式。

全部材料必须醒目标注：
“合成演示材料 / SYNTHETIC DEMO DOCUMENT / 不对应真实患者，不构成诊断或治疗建议。”
医院、患者、医生均必须是虚构标识；禁止使用真实医院、真实患者、真实截图、
真实二维码/签名/电话、API key、.env 或 runtime 文件。

必须实现生成、渲染、gold 标注、退化样本、legacy export、自动校验和统计报告脚本，
真实运行测试和校验命令后再提交。完成后向主开发提供 commit/PR、数据路径、
统计报告、验证结果与接入说明。
```

---

# 22. 本任务的原则总结

```text
事实图谱先于文档写作
结构化真源先于 PDF 渲染
Gold annotation 先于 OCR/LLM 效果展示
可追溯证据先于生成式回答
小批次完全验收先于大规模堆数据
公开合成数据安全先于一切功能数量
```

数据队友交付的不是一堆看起来像病历的 PDF，而是一套能够同时支撑：

```text
时间轴展示
OCR API 验证
原图证据高亮
摄像头质量检测
LLM 证据联查
自动化测试
路演复现
```

的 **可控、可验收、可扩展的合成转院材料数据工厂**。
