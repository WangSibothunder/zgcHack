# 转诊迹 v0.9 增量需求：OCR/LLM API 接入与“证据联查”模块（发送给 Codex）

> **适用仓库**：`WangSibothunder/zgcHack`  
> **产品展示名**：转诊迹｜转院病历证据时间轴  
> **本文件定位**：在 `docs/PRD_V0_8_ZHUANZHENJI.md` 基础上的新增需求，不推翻正在实现的采集、OCR、高亮和核验闭环。  
> **重要顺序**：若 v0.8 P0 仍未稳定，请先确保“真实合成图片上传 → 处理 → 时间轴插入 → 原图证据高亮 → 医生核验”可运行，再接入本文件中的证据联查功能。  
> **数据边界**：公开仓库与免费 API 调试阶段只能使用合成病例与合成文档，不得向第三方 API 上传真实患者材料。

---

## 1. 新增能力的产品定义

### 1.1 模块名称：证据联查

本轮新增功能不要命名为“AI 问诊”“智能诊断”或“治疗建议”。统一命名为：

```text
证据联查
基于已上传材料，定位与当前问题或选中文本相关的既往记录
```

### 1.2 价值主张

医生在转院接诊时，不仅要沿时间轴浏览材料，还会带着具体问题快速查找历史记录，例如：

- 病人近期是否有材料记录“食欲不振”或“进食减少”？
- 是否曾经有记录提到类似胸痛主诉？
- 当前选中的化验单字段，在既往材料中是否再次出现？
- 这页出院小结中提到的情况，之前哪份材料有对应记载？

系统不替医生回答医学问题，而是：

1. 把医生的问题转换为材料检索任务；
2. 找到与问题最相关的文档片段；
3. 列出该文档的日期、类型、科室/记录者（仅在原文中存在时显示）；
4. 展示与问题直接相关的原文片段和简短归纳；
5. 点击结果即可回到对应原图与 OCR bbox 证据位置；
6. 对没有明确证据的问题，诚实显示“当前上传材料中未检索到明确相关记载”。

### 1.3 输出边界

允许输出：

```text
在当前已上传材料中找到 2 条与“食欲不振”相关的明确记载：

- 2025-01-09｜门诊病历｜消化内科
  原文片段：“患者近一周食欲欠佳，进食量较前减少。”
  材料归纳：该条记录明确提到食欲欠佳及进食量减少。
  查看原图证据

- 2025-01-12｜入院记录｜内科
  原文片段：“食欲不振，否认明显呕吐。”
  材料归纳：该条记录再次出现食欲不振描述。
  查看原图证据
```

若原始记录中明确写有某位医生的判断，可这样展示：

```text
原文记载的判断：该记录中写有“考虑与近期治疗反应相关”。
说明：此内容为既往材料原文的归纳展示，并非本系统生成的新诊断。
```

禁止输出：

```text
患者确实存在食欲不振。
食欲不振可能由某疾病引起。
建议采取某项治疗或检查。
系统判断患者风险较高。
```

无结果时必须输出：

```text
在当前已上传材料中未检索到“食欲不振”或相关表述的明确记录。
这仅表示现有材料中未找到相关证据，不代表患者不存在该情况。
```

---

## 2. API 信息尚未补充时的处理原则

用户将补充可免费使用的 OCR API 与 LLM API 的具体文档、Base URL、模型名或调用示例。在收到准确 API 文档之前：

- 不要猜测实际 endpoint、鉴权 header 或响应字段；
- 先实现 Provider 接口、环境变量、mock/fallback 与单元测试；
- 当用户补充 API 文档后，只替换 provider adapter，不改动业务层与页面层；
- 免费 API 只能用于合成演示数据；
- 所有 API key 只能由本地 `.env` 注入，不得写入前端或提交至 public 仓库。

### 2.1 环境变量设计

新增 `.env.example`，只写占位符：

```bash
# 是否启用外部 API。public demo 默认 false；本地合成测试时可设置 true。
EXTERNAL_AI_ENABLED=false

# OCR provider
OCR_PROVIDER=mock
OCR_API_BASE_URL=
OCR_API_KEY=
OCR_API_MODEL=
OCR_API_TIMEOUT_SECONDS=30

# LLM provider
LLM_PROVIDER=mock
LLM_API_BASE_URL=
LLM_API_KEY=
LLM_API_MODEL=
LLM_API_TIMEOUT_SECONDS=45

# 仅允许 synthetic 数据进入外部 API
ALLOW_EXTERNAL_API_FOR_SYNTHETIC_ONLY=true
```

`.gitignore` 必须包含：

```gitignore
.env
.env.*
!.env.example
runtime/
demo-app/backend/runtime/
*.db
*.sqlite
*.sqlite3
```

### 2.2 后端安全拦截

在请求任何外部 OCR/LLM API 前，统一调用：

```python
assert_synthetic_external_api_allowed(case_or_material)
```

规则：

- `synthetic != true` 时拒绝调用外部 API；
- `ALLOW_EXTERNAL_API_FOR_SYNTHETIC_ONLY != true` 时拒绝调用；
- API 请求日志只记录 provider、耗时、状态码和 synthetic material id，不记录完整图片 base64、完整 OCR 文本或密钥；
- provider 调用失败时返回清晰的 fallback 状态，不得伪称外部 API 成功。

---

## 3. 用户交互需求：两种证据联查入口

## 3.1 入口 A：医生自然语言提问

### UI 位置

在“医生时间轴”页面顶部、患者转院信息区下方新增横向搜索框：

```text
证据联查：输入您希望在现有材料中查找的问题
[ 病人最近的材料中是否提到食欲不振？                      ] [查找相关记录]
```

搜索框下方固定小字：

```text
系统仅查找与归纳已上传材料中的相关证据，不生成诊断或治疗建议。
```

### 交互流程

```text
输入问题
→ 系统提取检索主题/同义表达
→ 在当前病例 OCR 文本片段中召回候选材料
→ LLM 仅对候选片段做相关性排序与证据摘要
→ 展示“关联文档 + 相关原文片段 + 摘要”
→ 点击结果回到时间轴节点并在原图高亮证据区域
```

### 示例问题

为合成演示新增一组能被检索的数据，不要使用真实患者：

```text
演示患者 B01 的材料中是否提到食欲欠佳？
当前记录中何时提到胸部不适？
既往材料是否写有需要转上级医院进一步评估？
哪些材料出现过相同的肌钙蛋白字段？
```

---

## 3.2 入口 B：医生选中某页图片或文字后查看关联文档

### UI 行为

在任意材料详情页或 OCR 文本区域：

- 医生点击一页图片：出现按钮 `查看与本页相关的记录`；
- 医生选中 OCR 文本片段：浮动按钮 `联查相关证据`；
- 医生点击结构化字段：在当前高亮证据之外，再出现 `历史关联记录` 区域。

### 结果呈现方式

结果不要覆盖原文。按照用户希望的“小字显示在文本下方”实现：

```text
OCR 原文：
“患者近一周食欲欠佳，进食量较前减少。”

关联记录（2）
└ 2024-12-20｜门诊病历：曾记录“纳差 3 日”     [查看证据]
└ 2025-01-12｜入院记录：再次记录“食欲不振”    [查看证据]
```

### 关联文档卡片必须显示

- 日期；
- 文档类型；
- 医院/科室/记录者：仅当材料明确提供时显示；
- 相关的原文短片段；
- 一句材料归纳；
- 相关性等级：`直接提及` / `同义表述` / `上下文相关`；
- OCR/提取置信度；
- `查看原图证据` 按钮；
- 是否由外部 LLM 辅助排序的透明标识。

### 点击联动

点击关联文档卡片：

- 时间轴滚动并激活对应时间节点；
- 打开对应材料；
- 在原图上高亮对应 bbox；
- 右侧显示 OCR 原文及医生核验状态。

---

## 4. 技术架构：LLM 不替代检索，更不能创造证据

### 4.1 强制采用“先检索，后归纳”的证据链路

不得将整份病例直接丢给 LLM 并要求它自由回答。必须实现以下链路：

```text
上传/预置合成材料
→ OCR blocks（每段文字保留 material_id、日期、页号、bbox）
→ 标准化 DocumentSegment 存储
→ 关键词/全文检索召回候选 segments
→ 可选 embedding 召回扩展候选
→ LLM 在候选范围内做相关性判别、排序和逐条短摘要
→ 返回每条结果对应的 segment_id 与 bbox
→ 前端展示关联材料并允许回到原图核验
```

核心规则：

- LLM 不能生成不存在的日期、文档、作者、字段或原文；
- 每条 LLM 输出必须绑定一个或多个 `segment_id`；
- 页面不得展示没有来源 segment 的内容；
- LLM 输出解析失败或无可核验来源时，回退到关键词检索结果；
- 原始 OCR 片段优先于 LLM 摘要展示。

### 4.2 为什么先做 hybrid retrieval，而不是全量大模型问答

本产品的主要卖点是可信追溯，不是开放问答。对于黑客松 Demo，以下实现最稳妥：

```text
第一层：SQLite FTS5 或后端关键词检索，确保基础召回可运行；
第二层：可选受控同义词扩展，如“食欲不振 / 食欲欠佳 / 纳差 / 进食减少”；
第三层：LLM 对 Top-K 候选做“是否与问题相关”判断及简短摘要；
第四层：点击任何结果均回到 OCR block 与原图 bbox。
```

如果外部 LLM API 不可用，第一层和第二层仍然能够演示基本证据联查。

---

## 5. 新增数据模型

## 5.1 DocumentSegment

每个 OCR block 或若干相邻 OCR blocks 组合成一个可检索片段：

```json
{
  "segment_id": "seg-caseA-mat03-p1-002",
  "case_id": "runtime-case-001",
  "node_id": "node-20250115",
  "material_id": "mat-003",
  "page_number": 1,
  "document_date": "2025-01-15",
  "document_type": "检验报告",
  "hospital_name": "青禾县中心医院（虚构）",
  "department": "心内科",
  "author_text": null,
  "raw_text": "肌钙蛋白 I：0.19 ng/mL ↑",
  "normalized_text": "肌钙蛋白 I 0.19 ng/mL 升高标记",
  "ocr_block_ids": ["ocr-b-002"],
  "bboxes": [[96, 312, 598, 361]],
  "ocr_confidence": 0.91,
  "synthetic": true,
  "source_mode": "external_ocr_api | deterministic_synthetic"
}
```

### 必须注意

- `author_text` 只能来源于文档明确文字；没有则为 `null`，不要编造“某某医生”；
- `document_date` 无法识别时设为 `null` 并显示“日期待确认”；
- `raw_text` 是证据正文，不能被 LLM 改写；
- `normalized_text` 只用于检索，不替代原文展示。

## 5.2 EvidenceQuery

```json
{
  "query_id": "query-001",
  "case_id": "runtime-case-001",
  "trigger_type": "question | selection | field",
  "question": "病人最近的材料中是否提到食欲不振？",
  "selected_segment_ids": [],
  "selected_material_id": null,
  "created_at": "2026-05-25T12:00:00Z",
  "synthetic": true
}
```

## 5.3 RelatedEvidenceItem

```json
{
  "rank": 1,
  "relevance_level": "direct_mention",
  "relevance_label": "直接提及",
  "material_id": "mat-digestive-002",
  "node_id": "node-20250109",
  "segment_id": "seg-digestive-002-p1-001",
  "document_date": "2025-01-09",
  "document_type": "门诊病历",
  "department": "消化内科",
  "source_excerpt": "患者近一周食欲欠佳，进食量较前减少。",
  "evidence_summary": "该条记录明确提到食欲欠佳及进食量减少。",
  "bbox": [110, 286, 710, 332],
  "ocr_confidence": 0.95,
  "ranking_source": "keyword+llm_rerank",
  "verification_status": "unreviewed"
}
```

## 5.4 EvidenceSearchResponse

```json
{
  "query_id": "query-001",
  "case_id": "runtime-case-001",
  "answer_mode": "evidence_only",
  "query_display": "食欲不振相关记录",
  "retrieval_terms": ["食欲不振", "食欲欠佳", "纳差", "进食减少"],
  "result_statement": "在当前已上传的合成材料中找到 2 条相关记录。",
  "items": [],
  "not_found_note": null,
  "llm_mode": "external_api | mock | unavailable_fallback",
  "notice": "以上为合成材料中的相关证据归纳，不构成诊断或治疗建议。"
}
```

当 `items=[]` 时：

```json
{
  "result_statement": "在当前已上传材料中未检索到明确相关记载。",
  "not_found_note": "这仅表示现有材料中未找到相关证据，不代表患者不存在该情况。"
}
```

---

## 6. 后端 API 设计

建议把本模块作为 `/api/v3/demo/`，避免与正在开发的 v2 ingestion 混淆。

## 6.1 为病例构建/刷新可检索片段

```http
POST /api/v3/demo/cases/{case_id}/segments/rebuild
```

作用：

- 从已有 fixtures 或 v2 ingestion OCR 结果构建 `DocumentSegment`；
- 保存到 runtime 的 SQLite/JSON index；
- 只处理 `synthetic=true` 的材料。

响应：

```json
{
  "case_id": "runtime-case-001",
  "segment_count": 38,
  "index_mode": "sqlite_fts5",
  "synthetic": true
}
```

## 6.2 医生问题检索

```http
POST /api/v3/demo/evidence-search
Content-Type: application/json
```

请求：

```json
{
  "case_id": "runtime-case-001",
  "trigger_type": "question",
  "question": "病人最近的材料中是否提到食欲不振？",
  "top_k": 5
}
```

响应使用 `EvidenceSearchResponse`。

## 6.3 选中页面或文字后的关联检索

仍使用同一接口：

```json
{
  "case_id": "runtime-case-001",
  "trigger_type": "selection",
  "selected_material_id": "mat-003",
  "selected_segment_ids": ["seg-caseA-mat03-p1-002"],
  "selected_text": "肌钙蛋白 I：0.19 ng/mL ↑",
  "top_k": 5
}
```

规则：

- 排除当前片段自身，或将自身独立放在“当前证据”区域；
- 结果只展示其他相关材料；
- 点击结果回到其来源原图高亮框。

## 6.4 获取 query 审计记录

```http
GET /api/v3/demo/cases/{case_id}/evidence-search-history
```

返回：

- 用户查询文本；
- 检索时间；
- 使用的 provider 模式；
- 返回的 segment ids；
- 不保存或展示诊断建议，因为系统不生成建议。

---

## 7. OCR API 接入要求

## 7.1 对正在实现的 v0.8 OCR Provider 的修改

如果 Codex 当前已经实现：

```python
OCRProvider.recognize(image_path) -> OCRResult
```

则只新增一个：

```python
ExternalOCRApiProvider
```

不要推翻现有 deterministic fallback。

### provider 输出最小要求

免费 OCR API 必须映射为统一输出：

```python
class OCRBlock(BaseModel):
    block_id: str
    text: str
    bbox: list[int] | None
    confidence: float | None

class OCRResult(BaseModel):
    provider_mode: str
    full_text: str
    blocks: list[OCRBlock]
    supports_bounding_boxes: bool
```

## 7.2 关键判断：OCR API 是否返回坐标

证据高亮依赖 bbox，因此 Codex 接入免费 OCR API 时必须先检查：

- API 是否返回每段文字位置；
- 坐标格式是四点 polygon 还是矩形框；
- 是否提供页码；
- 是否支持中文；
- 是否支持图片/PDF；
- 是否有免费调用频率限制与文件大小限制。

### 若 OCR API 返回 bbox

直接归一化为：

```text
[x_min, y_min, x_max, y_max]
```

供 EvidenceCanvas 渲染。

### 若 OCR API 只返回纯文本

该 API 可以用于：

- 时间轴文本生成；
- LLM 证据联查文本检索；

但**不能单独支撑原图高亮**。此时必须：

- 保留 sidecar bbox 演示数据，或
- 使用另一个能返回坐标的 OCR provider，或
- 在 UI 中明确写“该 API 模式下仅能回到材料页，无法定位到文字框”。

不得假装高亮来源来自 text-only API。

---

## 8. LLM API 接入与提示词约束

## 8.1 Provider 抽象

新增：

```python
class EvidenceLLMProvider(Protocol):
    async def rerank_and_summarize(
        self,
        query: str,
        candidate_segments: list[DocumentSegment],
    ) -> LLMGroundedResult:
        ...
```

实现：

```text
MockEvidenceLLMProvider             # 测试与离线演示
ExternalEvidenceLLMProvider         # 连接用户提供的免费 LLM API
```

如果 API 是 OpenAI-compatible，可在 provider 内部适配；如果不是，则按其官方文档写 adapter，但业务层不得依赖供应商特有字段。

## 8.2 LLM 的唯一任务

LLM 只能完成：

1. 识别问题中的检索主题与同义表述；
2. 在已召回的候选 OCR 片段中判断相关性；
3. 对每条证据生成一句不超出原文的短归纳；
4. 返回引用的 `segment_id`。

LLM 不允许完成：

- 新诊断；
- 新治疗建议；
- 病因推断；
- 基于缺失材料的否定结论；
- 没有 segment 支持的回答。

## 8.3 系统提示词模板

将模板保存为后端可测试常量或文件，例如：

```text
demo-app/backend/prompts/evidence_search_system.txt
```

内容要求如下：

```text
你是“转诊迹”中的证据联查模块，仅处理合成演示病历文本。
你的任务是从给定候选文档片段中筛选与医生问题直接相关的证据，并生成严格基于原文的简短归纳。

必须遵守：
1. 只能依据输入的候选片段，不得添加外部医学知识。
2. 不得给出诊断、治疗、检查建议或风险判断。
3. 不得声称患者存在或不存在某状况；只能说明材料是否有相关明确记载。
4. 文档中出现医生既往判断时，可以写“该记录原文记载……”，不得当作系统结论。
5. 每条结果必须引用 segment_id，并保留 source_excerpt。
6. 不确定或不相关时应排除；没有明确记录时返回空列表。
7. 只返回符合 JSON schema 的结果。
```

### LLM JSON 输出 schema

```json
{
  "expanded_terms": ["食欲不振", "食欲欠佳", "纳差", "进食减少"],
  "items": [
    {
      "segment_id": "seg-001",
      "relevance_level": "direct_mention | synonymous_mention | contextual",
      "evidence_summary": "该记录明确提到食欲欠佳及进食量减少。"
    }
  ]
}
```

后端必须校验：

- 返回的 `segment_id` 是否存在于 candidate segments；
- `evidence_summary` 是否长度合理；
- 每条结果最终展示时必须附回原始 `source_excerpt`、材料日期和 bbox；
- schema 验证失败则使用关键词召回顺序作为 fallback。

---

## 9. 检索与排序实现要求

## 9.1 P0 实现：SQLite FTS5 + LLM rerank

实现简单、稳定且能现场运行的方案：

```text
OCRResult
→ 切分 DocumentSegment
→ SQLite FTS5 索引 raw_text + normalized_text
→ query keyword/synonym recall Top 20
→ External LLM/Mock LLM rerank 为 Top 5
→ 返回可追溯 EvidenceSearchResponse
```

### 中文检索注意

若 SQLite FTS5 对中文分词效果不足，可在 Demo 中采用：

- 简单 substring 召回；
- 预定义同义词表；
- 每段存储 bigram 辅助字段；
- 后续再接 embedding，不要为了复杂向量库拖慢当前迭代。

## 9.2 受控同义词词典

为演示配置一个小型、只用于文档召回的词典：

```json
{
  "食欲不振": ["食欲欠佳", "纳差", "进食减少", "进食量减少"],
  "胸痛": ["胸部不适", "胸前区疼痛"],
  "转院": ["转上级医院", "转诊", "建议进一步诊治"],
  "肌钙蛋白": ["cTnI", "TnI", "肌钙蛋白 I"]
}
```

注意：这只是检索词扩展，不生成临床含义。

## 9.3 P1：embedding 检索

只有 P0 完成后再考虑：

- 若免费 LLM API 同时提供 embeddings，则新增 embedding provider；
- 或使用轻量中文 embedding 模型；
- 仍必须保留关键词召回作为离线 fallback；
- 不在 v0.9 P0 中引入复杂向量数据库。

---

## 10. 前端页面设计

## 10.1 时间轴页新增“证据联查”面板

推荐布局：

```text
┌──────────────────────────────────────────────────────────┐
│ 证据联查                                                  │
│ [ 病人最近的材料中是否提到食欲不振？              ][查找] │
│ 仅归纳已上传材料中的证据，不生成诊断或治疗建议。          │
├──────────────────────────────────────────────────────────┤
│ 检索结果：在当前材料中找到 2 条相关记录                   │
│                                                          │
│ 2025-01-09｜门诊病历｜消化内科        直接提及            │
│ “患者近一周食欲欠佳，进食量较前减少。”                  │
│ 归纳：该记录明确提到食欲欠佳及进食量减少。 [查看原图]    │
│                                                          │
│ 2025-01-12｜入院记录｜内科            同义表述            │
│ “食欲不振，否认明显呕吐。”                              │
│ 归纳：该记录再次出现食欲不振描述。       [查看原图]       │
└──────────────────────────────────────────────────────────┘
```

## 10.2 选中文本下方的小字关联记录

在 OCR 文本块与结构化字段下方支持：

```text
关联记录 2 条  ▾
  2024-12-20 门诊病历：曾记录“纳差 3 日”      查看证据
  2025-01-12 入院记录：记录“食欲不振”          查看证据
```

交互要求：

- 默认收起，不遮挡主要阅读；
- 展开后每条不超过两行；
- 点击“查看证据”执行 timeline 定位 + EvidenceCanvas 高亮；
- 显示 loading、无结果、API 失败 fallback 状态；
- 显示 `LLM 辅助排序` 或 `本地检索模式` 标识。

## 10.3 避免误导的措辞

页面上不要出现：

```text
AI 回答
智能诊断
建议处理
病情分析结论
```

统一使用：

```text
证据联查结果
材料归纳
原文记载
相关记录
查看原图证据
待医生核验
```

---

## 11. 合成演示数据补充

为体现“问题检索”能力，需要在 `demo-data/` 新增一套**完全虚构、明确带水印**的消化/肿瘤支持治疗转院案例，或在现有案例中谨慎补充分布式片段。

推荐新增：

```text
demo-evidence-query-appetite-001
```

材料节点示例：

| 日期 | 材料类型 | 合成原文片段 | 用途 |
| --- | --- | --- | --- |
| 2024-12-20 | 门诊病历 | “主诉：纳差 3 日。” | 同义检索命中 |
| 2025-01-09 | 门诊随访 | “近一周食欲欠佳，进食量较前减少。” | 直接相关 |
| 2025-01-12 | 入院记录 | “食欲不振，否认明显呕吐。” | 直接相关 |
| 2025-01-14 | 检查报告 | 与食欲无关的指标记录 | 验证系统不应误召回 |

所有图片需写明：

```text
合成演示材料 / SYNTHETIC DEMO DOCUMENT / 不对应真实患者
```

每个可命中的文本片段必须有：

- OCR blocks；
- bbox；
- sidecar fallback；
- expected query results，用于自动测试。

---

## 12. 自动化测试与验收

## 12.1 后端单元测试

新增测试：

- `ExternalOCRApiProvider` 在 mock HTTP 响应下正确映射 text、bbox 与置信度；
- text-only OCR 响应被标记为 `supports_bounding_boxes=false`；
- 外部 API 在非 synthetic 数据请求下被拒绝；
- LLM provider 返回的未知 `segment_id` 被丢弃；
- LLM 输出 schema 无效时回退到本地检索；
- `食欲不振` 查询可召回 `食欲欠佳` / `纳差` 合成片段；
- 无结果查询返回“未检索到明确相关记载”的安全文案；
- selection 查询不重复返回当前文档自身；
- 关联结果保留 bbox 并可链接到材料；
- API key 不出现在响应与日志中。

## 12.2 前端测试

新增测试：

- 证据联查搜索框可输入问题并触发 API；
- 结果卡片显示日期、文档类型、原文、材料归纳、查看证据；
- 无结果状态显示边界说明；
- 选中字段后出现关联记录区域；
- 点击关联结果定位时间轴节点并打开高亮证据；
- LLM provider 不可用时显示“本地检索模式”，页面仍可用；
- 页面不存在“诊断建议”“治疗推荐”等越界输出。

## 12.3 E2E 路演链路

必须覆盖：

```text
进入合成演示病例
→ 输入“病人最近的材料中是否提到食欲不振？”
→ 看到至少两条关联材料及原文片段
→ 点击 2025-01-09 材料的“查看原图证据”
→ 时间轴激活正确节点，图片中高亮对应 OCR bbox
→ 关闭弹窗，选中一段 OCR 文本并点击“联查相关证据”
→ 文本下方出现另一日期的关联材料
```

---

## 13. Codex 的实施顺序

### 阶段 1：不影响 v0.8 的基础接入

- 建立本文件与 API provider 环境变量；
- `.env.example`、`.gitignore` 与 public 数据拦截；
- 建立外部 OCR/LLM provider 接口及 mock provider；
- 若用户尚未补充具体 API 文档，只实现 adapter placeholder 和 mock，不猜 endpoint。

### 阶段 2：DocumentSegment 与本地证据检索

- 将预置/现场 OCR blocks 标准化为 segments；
- 构建本地索引；
- 完成关键词 + 受控同义词召回；
- 完成无 LLM 时可运行的 API 与 UI。

### 阶段 3：LLM grounded rerank

- 接入外部 LLM provider；
- 仅向 LLM 发送 synthetic query 与 Top-K candidate segments；
- 按 JSON schema 校验输出；
- 展示 `LLM 辅助排序` 标识；
- 故障回退到本地检索。

### 阶段 4：选择式关联与页面联动

- 文本/字段/文档页触发关联检索；
- 小字关联文档列表；
- 点击定位时间轴与证据高亮。

### 阶段 5：测试、文档与 push

- 运行后端、前端、E2E 测试；
- 更新 README 路演脚本；
- 更新完成报告并真实写出外部 API 是否成功接入、使用何种 provider；
- 检查无 key、无 `.env`、无 runtime、无真实数据后 push 至现有 public 仓库。

---

## 14. 直接发送给 Codex 的新增任务消息

```text
我补充一项紧急增量需求。请在完成或保持当前 v0.8 P0 可运行闭环的基础上，
读取并实施 docs/PRD_V0_9_EVIDENCE_LINKED_SEARCH.md。

新增模块正式名称为“证据联查”，不是 AI 问诊，也不是诊断建议。我们将使用可免费调用
的 OCR API 和 LLM API；具体 API 文档/Base URL/模型名若尚未提供，请先做 provider
抽象、.env.example、mock/fallback、测试和业务层，不要猜 endpoint，也不要把 key
写入 public 仓库。收到 API 文档后再只替换 adapter。

核心新增流程：
1. OCR API 必须尽可能保留文字 bbox；如果免费 API 只返回纯文本，必须诚实标识为
   不支持文字框定位，并保留 sidecar/现有 bbox 演示路径，禁止伪造定位来源。
2. 医生可在时间轴顶部提问，例如“病人最近的材料中是否提到食欲不振？”。
3. 医生也可选中某页材料、某段 OCR 文本或某个结构化字段，点击“联查相关证据”。
4. 系统只返回关联文档、日期、原文片段、严格基于原文的一句材料归纳与
   “查看原图证据”按钮，不输出诊断、病因推断、风险判断或治疗/检查建议。
5. LLM 必须采用“本地/关键词召回候选片段 → LLM 相关性排序与短摘要 →
   每条结果绑定 segment_id/bbox → 点击回到原图核验”的 grounded 流程；
   不允许将整份病历直接交给 LLM 自由回答。
6. 建立 DocumentSegment、EvidenceSearchResponse、review/audit 所需数据结构；
   加入一套带“食欲欠佳 / 纳差 / 食欲不振 / 无关文档”的全合成演示材料与测试。
7. UI 中结果显示为“证据联查结果 / 相关记录 / 材料归纳 / 查看原图证据”，
   不出现“AI 回答”“建议处理”“智能诊断”。
8. 仓库继续 public；外部 API 调用仅限 synthetic=true 材料；.env、token、
   runtime 文件和任何真实病例都不得提交。

完成后请运行实际测试与 E2E 链路，并在完成报告中如实说明：
- 使用的是外部 OCR API 还是真实 fallback；
- OCR API 是否返回 bbox；
- 使用的是外部 LLM API 还是本地检索 fallback；
- 哪些能力通过了真实浏览器演示；
- public 数据/密钥检查结果。
```

---

## 15. 本轮功能的路演表达

可以对评委这样介绍：

```text
转诊迹不替医生做诊断。医生在接诊时可以提出一个关心的问题，
例如“材料中是否记录过食欲不振”。系统会在已经上传的外院材料中找到相关原文，
告诉医生是哪一天、哪份文档、哪段文字出现了相关记录，并能一键回到原图高亮位置
进行核验。医生也可以选中当前病历中的某一页或某段文字，直接展开与其相关的历史
文档。这样，医生看到的不是一个无法验证的 AI 结论，而是一组能追溯到原始材料的
证据线索。
```
