# 转诊迹 v0.9.1 增量更新指导：接入 vivo 官方 OCR / BlueLM API（Codex 执行补丁）

> **适用仓库**：`WangSibothunder/zgcHack`（继续保持 public）  
> **依赖前置需求**：`docs/PRD_V0_8_ZHUANZHENJI.md` 与 `docs/PRD_V0_9_EVIDENCE_LINKED_SEARCH.md`  
> **本文件用途**：Codex 已经在执行 v0.9 的通用 Provider / 证据联查设计。本补丁只负责将“待确定的免费 API”具体化为 vivo 官方能力接入方案，不要求推翻已完成结构，不允许因为换 Provider 破坏现有 fallback 与测试。  
> **版本定位**：`v0.9.1 = v0.9 证据联查 + vivo API 可配置接入 + 接口事实核验与诚实降级`  
> **硬边界**：本版本仍然只处理带有明显水印的合成演示材料。不得将真实患者图片、真实病历文本或任何可识别个人信息发送给第三方 API 或提交至 public 仓库。

---

## 0. 给正在运行的 Codex 的即时处理原则

你可能已经开始实现 v0.9 的 Provider 抽象、DocumentSegment、证据检索或页面组件。收到本文件后请遵循：

1. **不要停止、重置或推翻当前 v0.9 实现**。若 `OCRProvider` / `EvidenceLLMProvider` / mock fallback 已建立，直接新增 vivo adapter。
2. **不要在尚未从官方文档核实字段之前猜写签名、endpoint、模型名或响应解析**。
3. 先将官方文档核验结论写入 `docs/VIVO_API_VERIFICATION.md`，再编写真实 provider。
4. 若运行环境暂时无 API 凭证，完成 adapter、mock response fixture、测试和 UI provider 状态展示；保持 deterministic fallback 可演示。
5. 若已有分支修改较多，优先以独立小提交接入，例如：
   ```text
   docs(vivo): verify official OCR and BlueLM API contract
   feat(provider): add vivo OCR and BlueLM evidence adapters
   test(provider): mock vivo signed API responses for evidence flow
   ```
6. 仓库保持 public，**禁止**提交 `APP_ID`、`APP_KEY`、真实返回日志、`.env` 或 runtime 数据。

---

# 1. 本次新增的官方 API 文档来源与核验状态

## 1.1 用户提供的比赛平台官方文档入口

Codex 应在浏览器中打开并逐字段阅读下列 vivo AIGC 创新赛官方文档页面：

```text
https://aigc.vivo.com.cn/#/document/index?id=1746
https://aigc.vivo.com.cn/#/document/index?id=1745
```

> 注：这些页面为前端动态加载页面，外部文本抓取工具不一定能读取正文。Codex 必须以浏览器中实际展示的官方文档为准，将必要字段手工记录为不含密钥的核验文档。

## 1.2 当前已经可核实的信息

以下信息可作为实现起点，但仍需在上述比赛文档中二次确认：

| 能力 | 已核实/已定位内容 | v0.9.1 的处理 |
| --- | --- | --- |
| vivo 通用 OCR | 官方开发者搜索结果可定位到“通用OCR”页面；可见主机为 `api-ai.vivo.com.cn`，URI 为 `/ocr/general_recognition`，请求方法为 `POST`。 | 新增 `VivoGeneralOCRProvider`，在正式编码请求与响应映射前核实文档字段。 |
| AI 原子能力文档 | 比赛相关通知中将 `id=1745` 标为 AI 原子能力入口。 | 用于核对 OCR 的鉴权、参数、返回定位框能力与调用限制。 |
| BlueLM / LLM 能力 | 用户已提供比赛官方文档入口，但当前自动抓取未能可靠读取正文。 | `VivoBlueLMEvidenceProvider` 必须在 Codex 实际读完官方页面并记录接口契约后接入；禁止凭经验猜路径。 |

## 1.3 Codex 必须建立接口核验记录

新增文件：

```text
docs/VIVO_API_VERIFICATION.md
```

该文件不得记录密钥，必须记录：

```markdown
# vivo API 接入核验记录

- 核验日期：
- 文档来源：vivo AIGC 创新赛官方页面 id=1745 / id=1746
- 核验人员：Codex-assisted implementation（由团队人工确认）

## OCR
- 能力名称：
- Host：
- URI：
- HTTP Method：
- 鉴权/签名方式：
- 请求 Content-Type：
- 图片传输格式：base64 / multipart / 其他
- 是否返回文本 bbox/polygon：
- 坐标返回字段：
- 置信度字段：
- 响应错误码结构：
- 文件格式/大小/频率限制：
- 对本项目 evidence highlight 的适用性：

## LLM / BlueLM
- 能力名称：
- Host：
- URI：
- HTTP Method：
- 鉴权/签名方式：
- Content-Type：
- 模型名称：
- prompt/messages/sessionId/requestId 等字段：
- 是否支持非流式：
- 响应文本字段：
- 响应错误码结构：
- 频率/token/并发限制：
- 对本项目 evidence rerank 的适用性：

## 本次采用策略
- 真实 OCR provider 是否启用：
- OCR 是否可提供 bbox：
- 真实 LLM provider 是否启用：
- 未启用功能及 fallback 原因：
```

只有当这份核验文件已填写到能够实现 provider 时，才能把 `VIVO_API_ENABLED` 打开。

---

# 2. v0.9.1 的目标：替换 provider，不替换产品逻辑

## 2.1 不变的业务主链路

v0.9 已定义的“证据联查”链路保持不变：

```text
合成材料上传 / 预置病例
→ OCR blocks（文本 + material_id + page + bbox 若可用）
→ DocumentSegment 索引
→ 医生提问或选择某一页/某段文字
→ 本地召回相关 segments
→ LLM 仅对候选证据排序并生成逐条材料归纳
→ 每条结果绑定 segment_id / material_id / bbox
→ 前端显示关联文档与原文片段
→ 医生点击回到原图证据并核验
```

vivo API 只作为：

- OCR 事实提取 provider；
- LLM grounded rerank / 简短归纳 provider。

vivo API 不得用于：

- 自动给出诊断；
- 推断患者病因；
- 给出检查或治疗建议；
- 对未上传材料作事实判断；
- 在没有来源 segment 的情况下生成回答。

## 2.2 Provider 优先级

系统必须支持以下组合：

| OCR 模式 | LLM 模式 | 展示标识 | 是否可演示 |
| --- | --- | --- | --- |
| vivo OCR 成功且返回 bbox | vivo BlueLM 成功 | `vivo OCR + BlueLM 辅助联查` | 首选 |
| vivo OCR 成功但不返回 bbox | vivo BlueLM 成功 | `vivo OCR 文本识别；图中定位能力受限` | 可演示检索，不得伪装高亮 |
| deterministic sidecar bbox | vivo BlueLM 成功 | `预置合成 OCR 坐标 + BlueLM 辅助联查` | 稳定后备 |
| vivo OCR 成功 | 本地检索 fallback | `vivo OCR + 本地证据检索` | 必须可用 |
| deterministic sidecar bbox | 本地检索 fallback | `离线合成演示模式` | 最终保底 |

任何 API 调用失败时，不得让核心 Demo 崩溃，应回落至可披露的 fallback 模式。

---

# 3. 环境变量与 public 仓库安全修改

## 3.1 `.env.example` 新增字段

若已有通用字段，不要重复定义；请向具体 vivo 配置收敛：

```bash
# ===== 外部能力总开关：仅本地运行时可启用 =====
EXTERNAL_AI_ENABLED=false
ALLOW_EXTERNAL_API_FOR_SYNTHETIC_ONLY=true

# ===== vivo 官方平台凭证（只放 .env，绝不提交）=====
VIVO_APP_ID=
VIVO_APP_KEY=

# ===== vivo OCR =====
VIVO_OCR_ENABLED=false
VIVO_OCR_HOST=api-ai.vivo.com.cn
VIVO_OCR_PATH=/ocr/general_recognition
# 下列参数必须以官方比赛文档核验结果为准后填写：
VIVO_OCR_BUSINESS_ID=
VIVO_OCR_POSITION_MODE=
VIVO_OCR_TIMEOUT_SECONDS=30

# ===== vivo BlueLM =====
VIVO_LLM_ENABLED=false
# 以下字段在读取官方文档后填写；不得凭非官方示例硬编码：
VIVO_LLM_HOST=
VIVO_LLM_PATH=
VIVO_LLM_MODEL=
VIVO_LLM_TIMEOUT_SECONDS=45
VIVO_LLM_STREAM=false

# ===== 演示与测试 =====
DEMO_RUNTIME_DIR=runtime
RUN_VIVO_LIVE_SMOKE=false
```

## 3.2 `.gitignore` 强制覆盖

Codex 必须检查并保证存在：

```gitignore
.env
.env.*
!.env.example

runtime/
demo-app/backend/runtime/
*.db
*.sqlite
*.sqlite3

# 禁止提交本地调试可能生成的请求/响应副本
*vivo_api_raw_request*
*vivo_api_raw_response*
*external_api_debug*
```

## 3.3 API 凭证使用原则

- `VIVO_APP_ID` 与 `VIVO_APP_KEY` 仅由后端读取；
- 前端永远不能获取或展示 app key；
- 前端只调用你们自己的 FastAPI 接口；
- public README 只能说明如何配置变量，不能出现真实值；
- 日志不得输出签名 header、完整 base64 图片或完整第三方响应；
- live smoke test 只允许使用合成样例。

---

# 4. 后端 Provider 实现需求

## 4.1 目录增量

若 v0.9 已有对应目录，直接加入文件；若无，则采用：

```text
demo-app/backend/
├─ providers/
│  ├─ base.py
│  ├─ synthetic_ocr.py                 # 原 fallback，必须保留
│  ├─ local_evidence_llm.py             # 原 fallback，必须保留
│  ├─ vivo_auth.py                      # 严格按官方样例实现签名
│  ├─ vivo_general_ocr.py               # v0.9.1 新增
│  └─ vivo_bluelm_evidence.py           # v0.9.1 新增
├─ services/
│  ├─ provider_registry.py
│  ├─ segment_index.py
│  └─ evidence_search.py
├─ schemas/
│  ├─ provider.py
│  └─ evidence_search.py
└─ tests/
   ├─ fixtures/vivo/
   │  ├─ ocr_success_with_bbox.json
   │  ├─ ocr_success_text_only.json
   │  ├─ llm_grounded_success.json
   │  └─ llm_invalid_segment.json
   ├─ test_vivo_ocr_provider.py
   └─ test_vivo_llm_provider.py
```

## 4.2 鉴权代码要求

### 核心规则

`vivo_auth.py` 必须来源于官方文档中的鉴权逻辑或对其进行最小封装，不得根据网上零散代码自行拼出“看起来能用”的签名。

实现完成后，在 `docs/VIVO_API_VERIFICATION.md` 记录：

- 签名函数来源于哪份官方文档；
- 使用哪些 header；
- 是否涉及时间戳、nonce、query parameters；
- 测试是否通过真实合成样例 smoke test。

### 安全规则

- 单元测试使用假的 `APP_ID`/`APP_KEY`；
- 对日志中的 credential/header 统一脱敏；
- 第三方调用异常中的请求对象不得原样返回给前端。

---

# 5. `VivoGeneralOCRProvider` 接入规范

## 5.1 已知起始配置

当前可先配置：

```python
VIVO_OCR_HOST = "api-ai.vivo.com.cn"
VIVO_OCR_PATH = "/ocr/general_recognition"
VIVO_OCR_METHOD = "POST"
```

上述内容需在 `docs/VIVO_API_VERIFICATION.md` 标记为已从官方开发者页面/比赛文档复核。

## 5.2 待官方文档核实后才能实现的字段

Codex 必须从用户提供页面中确认以下信息：

- 图片是否以 base64 字符串发送；
- body 使用 JSON 还是 form data；
- 是否存在 `pos` 或等价的“返回坐标”参数；
- 该参数哪些值对应“只返回文本 / 返回位置 / 同时返回文本和位置”；
- 是否需要 `businessid`，其值是否为文档公开固定配置或由账号生成；
- 返回坐标为 polygon 还是 rect；
- 是否返回识别置信度；
- 支持的图片格式、文件尺寸上限与调用限制。

## 5.3 统一 Provider 输出

无论 vivo 原始响应字段是什么，统一转换为现有系统结构：

```python
class OCRBlock(BaseModel):
    block_id: str
    text: str
    bbox: list[int] | None             # [x_min, y_min, x_max, y_max]
    polygon: list[list[int]] | None    # 若原响应返回四点，可同时保留
    confidence: float | None

class OCRResult(BaseModel):
    provider: Literal["vivo_general_ocr", "deterministic_synthetic"]
    provider_label: str
    full_text: str
    blocks: list[OCRBlock]
    supports_bounding_boxes: bool
    synthetic: bool
    raw_response_persisted: bool = False
```

### 坐标转换

若 vivo 返回四点坐标：

```python
x_min = min(point.x for point in polygon)
y_min = min(point.y for point in polygon)
x_max = max(point.x for point in polygon)
y_max = max(point.y for point in polygon)
bbox = [x_min, y_min, x_max, y_max]
```

### 重要降级逻辑

如果官方接口或当前配置只能获得文本而不能获得坐标：

- `supports_bounding_boxes=false`；
- 该材料可以进入文本检索与 LLM 证据联查；
- 不得为该材料展示伪造的高亮框；
- UI 需显示：`当前 OCR 模式可提取文本，但未返回可用于原图定位的文字坐标。`;
- 现场路演若必须展示高亮，应选择 sidecar bbox 合成样例模式，并标注数据来源。

---

# 6. `VivoBlueLMEvidenceProvider` 接入规范

## 6.1 不能提前硬编码的部分

LLM 文档正文需要 Codex 在官方页面打开后核对。因此，在核验前禁止固定：

- LLM 的 host/path；
- 可用模型名；
- 是否通过 `prompt` 或 `messages` 输入；
- 是否必须带 `sessionId` / `requestId`；
- stream 或非 stream 响应格式；
- 鉴权字段；
- token 或调用频率参数。

## 6.2 本项目只使用非流式、结构化输出

若官方 API 支持非流式模式，v0.9.1 必须优先使用非流式。原因：

- 证据排序结果需要 JSON schema 校验；
- 流式输出会增加解析和失败恢复复杂度；
- 现场 Demo 更重视可核验稳定性，而不是逐字生成动画。

若官方文档只提供流式调用，则 Codex 需：

- 封装流式数据读取；
- 聚合完整 JSON 后再校验；
- 未能解析结构化 JSON 时自动回退本地检索；
- 在完成报告中记录这一限制。

## 6.3 发送给 BlueLM 的内容最小化

BlueLM 仅接收：

- 医生输入的问题；
- Top-K 候选合成 `DocumentSegment` 的 `segment_id` 与 `raw_text`；
- 必要的日期/材料类型元数据；
- 严格系统提示词。

禁止发送：

- 整个病例库；
- 原始图片；
- 不相关 OCR 内容；
- 未来的真实患者文本；
- 鉴权密钥以外的运行日志。

请求中的合成候选片段示例：

```json
{
  "query": "病人最近的材料中是否提到食欲不振？",
  "candidate_segments": [
    {
      "segment_id": "seg-001",
      "date": "2025-01-09",
      "document_type": "门诊病历",
      "raw_text": "患者近一周食欲欠佳，进食量较前减少。"
    },
    {
      "segment_id": "seg-002",
      "date": "2025-01-14",
      "document_type": "检查报告",
      "raw_text": "检查材料中的无关描述。"
    }
  ]
}
```

## 6.4 必须使用的系统提示词

保存为：

```text
demo-app/backend/prompts/vivo_evidence_linked_search_system.txt
```

提示词：

```text
你是“转诊迹”中的证据联查排序模块。本次输入全部为带水印的合成演示病历文本。

你的唯一任务：
从给定 candidate_segments 中筛选与医生查询直接相关或具有明确同义表述的材料片段，
按相关性排序，并为每条被选中的片段生成一句严格基于原文的“材料归纳”。

严格规则：
1. 你只能依据 candidate_segments，不得加入外部医学知识。
2. 不得输出诊断、疾病判断、病因推断、风险判断、检查建议或治疗建议。
3. 不得声称患者确实存在或不存在某情况；只能说明某份材料是否有相关明确记载。
4. 若候选原文中已有既往医生判断，只能写“该记录原文记载……”，不得改写为本系统判断。
5. 每条结果必须返回输入中真实存在的 segment_id。
6. evidence_summary 不得比 source_excerpt 表达更强的结论。
7. 没有明确相关证据时，items 必须返回空数组。
8. 只输出 JSON，不要输出 markdown 或额外解释。

返回 JSON schema：
{
  "expanded_terms": ["用于解释召回的同义表述"],
  "items": [
    {
      "segment_id": "必须来自输入",
      "relevance_level": "direct_mention | synonymous_mention | contextual",
      "evidence_summary": "一句仅复述材料含义的短归纳"
    }
  ]
}
```

## 6.5 后端强校验

LLM 响应必须经过以下校验：

- 必须能解析为 JSON；
- `segment_id` 必须属于本次发送的候选集合；
- `relevance_level` 必须在允许枚举内；
- `evidence_summary` 必须非空且长度受限，例如 `<= 100` 字；
- 展示给用户时，摘要旁必须附后端保存的原始 `source_excerpt`；
- 任意校验失败则丢弃 LLM 返回，回退至本地检索排序。

---

# 7. 新增 Provider 状态接口与前端透明披露

## 7.1 状态 API

新增：

```http
GET /api/v3/demo/providers/status
```

响应示例：

```json
{
  "synthetic_only": true,
  "ocr": {
    "configured": true,
    "enabled": true,
    "provider": "vivo_general_ocr",
    "label": "vivo 通用 OCR",
    "supports_bounding_boxes": true,
    "last_smoke_test": "passed"
  },
  "llm": {
    "configured": true,
    "enabled": true,
    "provider": "vivo_bluelm",
    "label": "vivo BlueLM 证据排序",
    "last_smoke_test": "passed"
  },
  "fallback_available": true,
  "notice": "仅对合成演示材料调用外部能力。"
}
```

未经真实 smoke test 时不得返回 `passed`。

## 7.2 前端标识

在“采集新材料”页与“证据联查”结果区增加 provider 徽标：

| 场景 | 前端显示 |
| --- | --- |
| vivo OCR 实际成功调用 | `vivo OCR 识别` |
| sidecar fallback | `预置合成 OCR 回放` |
| vivo BlueLM 实际成功排序 | `BlueLM 辅助排序` |
| 本地检索 fallback | `本地证据检索` |
| OCR 无 bbox | `当前识别未提供原图文字定位` |

禁止界面在 fallback 情况下展示 `vivo OCR 已识别` 或 `BlueLM 已分析`。

---

# 8. API 路由与服务层调整

## 8.1 不改现有业务 API 的前提下新增能力

若 v0.9 已实现以下接口，沿用并只修改内部 provider 路由：

```http
POST /api/v3/demo/cases/{case_id}/segments/rebuild
POST /api/v3/demo/evidence-search
GET  /api/v3/demo/cases/{case_id}/evidence-search-history
```

新增：

```http
GET  /api/v3/demo/providers/status
POST /api/v3/demo/providers/vivo/smoke-test
```

## 8.2 Smoke test 设计

```http
POST /api/v3/demo/providers/vivo/smoke-test
```

请求：

```json
{
  "run_ocr": true,
  "run_llm": true,
  "sample_id": "cardiac_lab_clear",
  "synthetic_acknowledged": true
}
```

限制：

- 只有 `RUN_VIVO_LIVE_SMOKE=true` 且本地配置凭证时可调用；
- 固定使用合成材料；
- 不从前端上传真实用户材料；
- 响应只返回通过/失败与安全摘要，不返回签名、原始完整请求或密钥；
- 运行次数应由页面提示用户控制，避免无意义消耗免费额度。

响应示例：

```json
{
  "ocr": {
    "attempted": true,
    "passed": true,
    "provider": "vivo_general_ocr",
    "bbox_available": true
  },
  "llm": {
    "attempted": true,
    "passed": true,
    "provider": "vivo_bluelm",
    "grounded_schema_valid": true
  },
  "synthetic": true
}
```

---

# 9. 测试要求：先 mock，后 live smoke

## 9.1 不依赖额度的自动化测试

必须通过 mock HTTP 或 dependency injection 测试：

### OCR provider

- 签名构建函数使用假凭证不泄露 key；
- 官方响应 fixture 能映射为 `OCRResult`；
- 若响应含位置，能归一化为 bbox；
- 若响应无位置，`supports_bounding_boxes=false`；
- provider 超时或 API 错误时可回退且给出准确状态。

### LLM provider

- 请求中仅包含医生 query 与 Top-K synthetic segments；
- 请求 system prompt 含医疗边界约束；
- 合法 JSON 结果可映射为关联证据；
- 返回不存在的 `segment_id` 时结果被拒绝；
- 返回诊断/建议型内容或非 JSON 时触发 fallback；
- provider 失败不会阻塞页面显示本地召回证据。

### 安全测试

- `synthetic=false` 的材料拒绝外部 provider；
- `.env`、raw response、runtime 文件不在 tracked files 中；
- response/log 不包含 APP_KEY；
- 公共前端 bundle 不包含 vivo key。

## 9.2 Live smoke test

仅在本地手动运行，且仅使用合成样例：

```bash
export EXTERNAL_AI_ENABLED=true
export VIVO_OCR_ENABLED=true
export VIVO_LLM_ENABLED=true
export RUN_VIVO_LIVE_SMOKE=true
# APP_ID / APP_KEY 仅注入当前 shell 或本地 .env，不提交
```

需要在完成报告中真实记录：

| 测试项 | 结果 | 备注 |
| --- | --- | --- |
| vivo OCR 是否成功返回文本 | pass/fail/not run | |
| vivo OCR 是否返回 bbox/polygon | yes/no/not verified | |
| vivo BlueLM 是否成功返回 grounded JSON | pass/fail/not run | |
| API failure 时 fallback 是否可用 | pass/fail | |
| 测试材料是否为 synthetic | yes | |

---

# 10. UI 演示流程的小版本修订

v0.9.1 路演时，显示外部 API 能力但不夸大：

```text
1. 打开“转诊迹”，页面显示当前仅处理合成演示材料。
2. 在采集页上传或摄像头拍摄带水印的合成病历。
3. 若配置了 vivo OCR：展示“vivo OCR 识别”标签，并生成文本；若返回文字坐标，点击字段可见原图高亮。
4. 若未配置/调用失败：显示“预置合成 OCR 回放”，流程仍可演示。
5. 医生输入：“病人最近的材料中是否提到食欲不振？”
6. 页面先检索既往材料，再由 BlueLM（若启用）辅助排序相关证据。
7. 结果只显示日期、材料、原文片段与材料归纳，并可以查看原图证据。
8. 若 BlueLM 未配置或失败，展示“本地证据检索”，不影响结果浏览。
9. 医生点击确认/需复核，摘要页同步状态。
```

演示讲解可以说：

```text
我们接入 vivo 提供的 OCR 与 BlueLM 能力，但系统的定位不是给医生一个黑箱建议。
OCR 将材料转成可定位的文本证据，BlueLM 只在已检索出的候选片段中帮助排序和归纳。
任何展示给医生的关联结果，都必须链接到具体文档与原文位置；如果外部 API 不可用，
系统会透明切换至合成回放或本地检索，而不会伪称完成了识别或分析。
```

---

# 11. 文档修改清单

Codex 应追加或更新：

```text
docs/PRD_V0_9_1_VIVO_API_INTEGRATION.md      # 本文件
docs/VIVO_API_VERIFICATION.md                 # 官方文档核验结果，禁止写 key
docs/API_CONTRACT_V3.md                       # 增加 provider status / smoke test
docs/PUBLIC_DATA_POLICY.md                    # 写明外部 API 仅允许 synthetic
docs/DEMO_V0_9_1_COMPLETION_REPORT.md         # 真实 provider 与测试结果
README.md                                     # 增加 vivo API 可选接入与演示模式说明
.env.example                                  # 凭证占位与开关
.gitignore                                    # 密钥/runtime/raw response 防护
```

README 必须区分：

```text
默认公开演示模式：离线、全合成、无需 API 凭证。
本地增强演示模式：配置本人获得的 vivo 凭证后，仅对合成材料调用 vivo OCR / BlueLM。
真实医疗数据：本仓库与本 Demo 均不支持上传或处理。
```

---

# 12. 完成定义（Definition of Done）

## 12.1 必须完成

- [ ] v0.9 原有证据联查业务链路没有被破坏；
- [ ] `docs/VIVO_API_VERIFICATION.md` 已依据官方页面填写，且不包含密钥；
- [ ] `.env.example` 与 `.gitignore` 更新完成；
- [ ] 后端新增 `VivoGeneralOCRProvider`，或在官方字段仍无法核实时明确保留 placeholder 并记录阻塞；
- [ ] 后端新增 `VivoBlueLMEvidenceProvider`，或在官方字段仍无法核实时明确保留 placeholder 并记录阻塞；
- [ ] 外部 provider 仅允许处理 `synthetic=true` 材料；
- [ ] UI 真实显示当前使用的是 vivo API 还是 fallback；
- [ ] OCR 无 bbox 时不展示伪造文字框；
- [ ] BlueLM 输出仅用于有 segment 证据的排序/归纳；
- [ ] provider mock 自动化测试通过；
- [ ] 如凭证可用，完成仅针对合成材料的 live smoke test，并真实记录结果；
- [ ] public 仓库检查通过，无 `.env`、key、runtime、raw API payload、真实患者数据；
- [ ] 更新 README 和完成报告后 push 到现有 public `zgcHack` 仓库。

## 12.2 不得宣称的内容

在未真实验证前不得写：

- `vivo OCR 已成功识别`；
- `BlueLM 已接入并运行`；
- `OCR 支持 bbox 定位`；
- `API 免费额度足够现场使用`；
- `可处理真实患者数据`；
- `实现医学分析或临床建议`。

允许诚实写：

- `已完成 vivo API adapter 与 mock 测试，等待配置本地凭证进行 synthetic smoke test`；
- `在 API 不可用时，系统支持预置合成 OCR 与本地检索降级演示`；
- `本仓库仅面向公开的合成材料流程展示`。

---

# 13. 直接发送给正在运行的 Codex 的补丁消息

复制下面消息发送给 Codex：

```text
补充小版本更新：请在当前正在实施的 v0.9“证据联查”基础上，新增并读取
`docs/PRD_V0_9_1_VIVO_API_INTEGRATION.md`，不要推翻或重做已经完成的通用 Provider、
DocumentSegment、本地检索、UI 与测试结构。

我现在已提供 vivo AIGC 创新赛官方 API 文档入口：
- https://aigc.vivo.com.cn/#/document/index?id=1746
- https://aigc.vivo.com.cn/#/document/index?id=1745

请先在浏览器实际阅读官方页面，将 OCR 与 BlueLM 的 Host、URI、Method、鉴权签名、
请求字段、响应字段、bbox/坐标能力、模型名、stream 能力与限制整理到
`docs/VIVO_API_VERIFICATION.md`（禁止写入任何真实 APP_ID/APP_KEY）。经官方文档
核实后，再实现 `VivoGeneralOCRProvider` 与 `VivoBlueLMEvidenceProvider`。

当前已经可作为起始核验项的信息：vivo 官方通用 OCR 页面可定位到
`api-ai.vivo.com.cn` + `/ocr/general_recognition`，方法为 `POST`；但图片 body 字段、
位置参数、business id、鉴权和响应结构仍必须以你实际读取的官方文档为准。

实现要求：
1. `.env.example` 中增加 VIVO_APP_ID、VIVO_APP_KEY、OCR/LLM host/path/model 和开关；
   `.gitignore` 禁止提交 `.env`、runtime、数据库与 raw API 调试响应。
2. 外部 API 仅允许调用 `synthetic=true` 的带水印合成材料；真实患者材料永远不能
   进入本 public demo 或第三方 API。
3. OCR provider 若能从官方接口获得文字坐标，则映射为统一 bbox 并用于原图高亮；
   若 API 只返回纯文本，UI 必须明确显示“当前识别未提供原图文字定位”，不得伪造框。
4. BlueLM 只能接收医生 query 与本地召回后的 Top-K 合成 DocumentSegment；
   只能做相关性排序与基于原文的一句材料归纳。每条输出必须绑定输入中存在的
   segment_id；无可核验来源、JSON 无效或出现诊断/建议式输出时，回退本地检索。
5. 新增 provider status 与 synthetic-only smoke-test 能力；页面展示当前真实运行模式：
   vivo OCR / 预置合成 OCR 回放，BlueLM 辅助排序 / 本地证据检索。
6. 自动化测试使用 mock vivo 响应，不消耗额度；若本地凭证可用，仅用合成材料运行
   live smoke test，并在 `docs/DEMO_V0_9_1_COMPLETION_REPORT.md` 中如实记录是否
   调通、OCR 是否返回 bbox、LLM 是否返回合法 grounded JSON。
7. 更新 README，写清默认离线合成演示模式与可选 vivo API 增强演示模式；完成测试、
   安全检查后继续 push 到现有 public `zgcHack` 仓库。
```

---

# 14. 开发判断优先级

本补丁的优先级规则为：

```text
官方文档核实 > 猜测式快速接入
证据可追溯 > 大模型回答华丽
透明降级可演示 > 隐藏失败假装成功
合成材料安全 > API 功能数量
v0.9 主链路稳定 > 为换 provider 大规模重构
```

v0.9.1 完成后，项目应能诚实地展示：

> **转诊迹通过 vivo OCR 将合成转院材料转为可定位的文本证据，并通过 BlueLM 对医生问题相关的既往材料进行受约束的辅助筛选与归纳；所有结果必须回到具体原文与原图核验，系统不生成医学诊断或治疗建议。**
