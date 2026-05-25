# 转诊迹 v0.9.1-Resolved：vivo OCR / LLM 已核实接口接入补丁（Codex 立即追加执行版）

> **用途**：你正在执行 `docs/PRD_V0_9_EVIDENCE_LINKED_SEARCH.md` 与此前的 `docs/PRD_V0_9_1_VIVO_API_INTEGRATION.md`。此前 v0.9.1 中将 vivo API 具体字段写成了“需要阅读官方页面后再核实”。现在用户已直接提供官方文档正文，请以本文件中的已核实接口为准，补齐 provider，不要推翻已完成的 v0.8/v0.9 主结构。  
> **建议保存路径**：`docs/PRD_V0_9_1_VIVO_API_RESOLVED_PATCH.md`  
> **仓库策略**：仓库继续保持 public；外部 API 只允许处理带明显水印的 `synthetic=true` 合成演示材料。  
> **产品边界**：OCR 负责读取文字与位置；LLM 只负责候选证据排序与严格基于原文的材料归纳；本系统不输出诊断、风险判断、检查建议或治疗建议。

---

## 0. 收到本补丁后的执行方式

1. **不停止当前实现，不回滚 v0.9 的通用架构。** 若已经有 `OCRProvider`、`EvidenceLLMProvider`、`DocumentSegment`、本地检索、证据联查 UI 和 fallback，直接增加/修订 vivo provider。
2. 用本文件替换原 v0.9.1 中“待核实”的接口字段，并将已核实信息同步填写到 `docs/VIVO_API_VERIFICATION.md`。
3. 先完成 mock 测试，再使用本地 `.env` 中的真实 AppKey 对**合成材料**运行 smoke test。
4. API 测试失败时必须透明降级到 sidecar OCR / 本地检索，不允许让 Demo 崩溃，也不允许伪称外部 API 成功。
5. 若当前 Codex 迭代已进入提交阶段，请新增一个独立 commit 完成本补丁，避免破坏已有可运行状态。

---

# 1. 已核实 API 契约摘要

## 1.1 vivo 通用 OCR：已核实字段

| 项目 | 官方文档给出的值 | 项目实现决定 |
| --- | --- | --- |
| 服务名称 | 通用 OCR | Provider 名称：`VivoGeneralOCRProvider` |
| 接口地址 | `http://api-ai.vivo.com.cn/ocr/general_recognition` | 优先先测试相同路径是否支持 `https://`；若只支持官方文档中的 `http://`，只允许 synthetic demo 调用，并在完成报告中记录传输安全限制 |
| 请求方式 | `POST` | `requests.post(...)` |
| Content-Type | `application/x-www-form-urlencoded` | 使用 form body，不发送 JSON |
| 鉴权 | `Authorization: Bearer AppKey` | AppKey 仅后端读取 |
| Query 参数 | `requestId`，必须，UUID | OCR 严格按 `requestId` 发送 |
| Body：`image` | 必须，图像 base64；支持 jpg/png/bmp | 上传材料转 base64 后发送 |
| Body：`pos` | 必须，`0/1/2`；文档建议 `pos=2` | 本项目默认固定 `pos=2`，因为需要文本和位置 |
| Body：`businessid` | 必须，文档写为 `"aigc" + appid` | 默认生成 `aigc{VIVO_APP_ID}`；同时允许 env 覆盖以便按赛事账号配置核验 |
| Body：`sessid` | 可选，UUID，前端传递 | 后端为每一页材料生成 UUID 并提交 |
| 返回：`error_code` | `0` 成功，`1` OCR 失败，`2` 图像错误 | 映射为 provider success/error |
| 返回：`result` | `pos=2` 提供文字与坐标信息；坐标为相对值 | 转换为系统 `OCRBlock` 与 overlay 坐标 |
| 返回：`angle` | 可能为 `0/90/180/270` | 保存方向信息，绘制证据前处理坐标方向或记录为待处理 |
| OCR 置信度 | 用户提供的文档中**未列出**置信度字段 | live vivo OCR 的 `confidence=null`，不得伪造分数 |

### 重要修正 1：OCR 可以支持原图证据位置

此前补丁将“是否返回 bbox”留作待核验项。现在已确认：

- `pos=1`：文字和绝对坐标；
- `pos=2`：同时提供文字与坐标，坐标为相对值，官方建议使用 `pos=2`。

因此，**现场合成材料使用 vivo OCR 时应请求 `pos=2`，并以响应位置绘制原图证据高亮。**

### 重要修正 2：不得给 live OCR 伪造置信度

当前官方文档描述的响应包含文字、位置与方向角度，但没有说明识别置信度字段。因此：

- 预置 fixture/sidecar 若已有用于演示的置信度，可显示为 `预置演示置信度`；
- vivo OCR live 结果必须显示：`位置由 vivo OCR 返回；该接口响应未提供 OCR 置信度`；
- 不要继续沿用静态数据中的 `0.91` 作为 live 请求输出。

### 重要修正 3：HTTP 传输风险必须披露

OCR 官方文档提供的访问地址为 `http://...`，而鉴权使用 Bearer AppKey、图片为 base64。对真实医疗数据而言，这不符合本项目所需的数据安全要求。

Codex 必须：

1. 用 synthetic 样例先测试 `https://api-ai.vivo.com.cn/ocr/general_recognition` 是否可用；
2. 若 HTTPS 可用，使用 HTTPS；
3. 若只能使用官方文档列出的 HTTP：
   - 仅允许本次合成 Demo 的临时测试；
   - README 与完成报告标注：当前 OCR 外部调用仅用于合成演示，真实数据接入前必须解决加密传输与合规部署问题；
   - 绝不上传真实患者材料。

---

## 1.2 vivo 大模型接口：已核实字段

| 项目 | 官方文档给出的值 | 项目实现决定 |
| --- | --- | --- |
| 接口地址 | `https://api-ai.vivo.com.cn/v1/chat/completions` | Provider 名称：`VivoEvidenceLLMProvider` |
| 协议 | 支持主流 OpenAI 协议格式、Responses API 协议格式和三方自定义格式 | 本项目使用 OpenAI-compatible Chat Completions |
| 请求方式 | `POST` | 使用 `openai` Python client 或 `requests` 均可；优先复用项目已有 HTTP 方式 |
| Content-Type | `application/json` | 后端发送 JSON |
| 鉴权 | `Authorization: Bearer AppKey` | 只从后端 `.env` 读取 |
| Query 参数 | 表格写 `requestId`；官方 Python 与 requests 示例使用 `request_id` | 这是文档内部不一致：provider 默认使用示例中的 `request_id`，若返回缺参错误 1001，仅进行一次兼容重试改用 `requestId`，并将最终字段记录在完成报告 |
| 可用模型 | `Volc-DeepSeek-V3.2`、`Doubao-Seed-2.0-mini`、`Doubao-Seed-2.0-lite`、`Doubao-Seed-2.0-pro`、`qwen3.5-plus` | 模型必须由 env 配置，禁止散落硬编码 |
| `messages` | 支持 system、user；content 可为 string/object | 证据联查使用 system + user，两条消息足够 |
| `stream` | `true/false` | 证据联查固定 `false`，便于 JSON 校验 |
| `max_tokens` | 可选，默认 4096 | 设为小值，例如 `1024` |
| `max_completion_tokens` | 可选，范围 `[0,65536]` | 本阶段无需使用或限制较小 |
| `reasoning_effort` | `minimal/low/medium/high`，默认 `minimal` | 证据排序应使用 `minimal`，减少延迟 |
| `tools` | 文档列为可选参数 | v0.9.1 不需要使用 tools/function calling |
| 错误码 | `1001` 参数异常；`1007` 审核干预；`30001` 无权限或限流；`2003` 单日用量限制 | 映射为可解释 provider 状态与 fallback |

### 模型推荐

本功能不是复杂推理，而是“对已经召回的候选材料进行相关性判断和一句材料归纳”，因此优先考虑低延迟和结构化稳定性：

```bash
VIVO_LLM_MODEL=qwen3.5-plus
VIVO_LLM_ENABLE_THINKING=false
```

若 `qwen3.5-plus` 当前账号无权限或 JSON 稳定性不理想，再通过环境变量切换：

```bash
VIVO_LLM_MODEL=Volc-DeepSeek-V3.2
VIVO_LLM_REASONING_EFFORT=minimal
```

Codex 不要在代码中假设某个模型始终可用，应由 smoke test 与完成报告说明最终成功调用的模型。

---

## 1.3 Function Calling 文档对本项目的结论

用户还提供了 vivo 的 Function Calling 使用指南。该指南说明：

- function call 通过 `messages` 组织调用；
- 直接 API 使用时，需要开发者自行封装 system 中的 API 描述并解析模型输出；
- 示例使用 `<APIs>[{"name": "...", "parameters": {...}}]</APIs>` 作为 assistant 触发工具调用的文本格式；
- function 返回结果再通过 `role: function` 放回后续 messages。

### v0.9.1 决策：当前不要引入 Function Calling

证据联查不需要模型自行决定调用什么工具。本项目的后端业务流程本就应确定为：

```text
后端接收医生查询
→ 后端执行本地 segment 召回
→ 后端将候选片段送给 LLM 做排序与摘要
→ 后端严格校验 segment_id
→ 返回前端
```

因此，本版本：

- **不使用 Function Calling 来触发 OCR、检索或原图查看**；
- **不让 LLM 决定是否查询某个文档**；
- **不额外解析 `<APIs>...</APIs>`**；
- 仅使用普通 `chat/completions` 输出受约束 JSON。

原因：

1. 后端固定编排更容易保证每条输出绑定真实证据；
2. Function Calling 会增加解析失败和模型自主调用带来的不确定性；
3. 路演重点是可信追溯，不是 agent 自主工具选择；
4. 当前时间紧张，最优路线是把真实 OCR + grounded evidence search 做稳。

Function Calling 可作为比赛结束后的 roadmap：未来当系统有“查找某类材料”“打开某节点”“生成补充材料清单”等多工具操作时，再考虑受控接入。

---

# 2. 用本补丁修订原 v0.9.1 任务

## 2.1 立即删改原有待核验内容

在 `docs/VIVO_API_VERIFICATION.md` 中将以下字段从“待核实”更新为“已由用户提供的官方文档正文确认”：

```markdown
## OCR 接口核验结论
- 能力名称：通用 OCR
- Endpoint：http://api-ai.vivo.com.cn/ocr/general_recognition
- Method：POST
- Content-Type：application/x-www-form-urlencoded
- Authorization：Bearer AppKey
- Query：requestId=<uuid>
- Body.image：base64 字符串，支持 jpg/png/bmp
- Body.pos：0/1/2；本项目使用 2
- Body.businessid："aigc" + AppId（允许 env override）
- Body.sessid：可选 UUID
- 是否返回位置：是；pos=2 返回可用于定位的信息
- 是否返回置信度：提供的文档中未发现该字段，live UI 不展示伪造置信度
- 重要安全限制：官方地址为 HTTP；只允许 synthetic demo 调用，优先测试同路径 HTTPS 可用性

## LLM 接口核验结论
- 能力名称：大模型 / Chat Completions
- Endpoint：https://api-ai.vivo.com.cn/v1/chat/completions
- Method：POST
- Content-Type：application/json
- Authorization：Bearer AppKey
- Query 参数：文档表格为 requestId，代码示例为 request_id；需在 synthetic smoke test 中确定有效字段
- 支持协议：OpenAI-compatible Chat Completions
- 可配置模型：Volc-DeepSeek-V3.2 / Doubao-Seed-2.0-mini / Doubao-Seed-2.0-lite / Doubao-Seed-2.0-pro / qwen3.5-plus
- 本项目调用模式：stream=false，低温度，关闭/最小思考，输出 JSON
- Function Calling：本版本不接入，固定由后端编排检索和证据绑定
```

---

# 3. 环境变量最终版

更新 `.env.example`：

```bash
# ==============================
# 公开 Demo 的外部能力开关
# ==============================
EXTERNAL_AI_ENABLED=false
ALLOW_EXTERNAL_API_FOR_SYNTHETIC_ONLY=true

# ==============================
# vivo API credentials
# 仅写入本地 .env，不提交真实值
# ==============================
VIVO_APP_ID=
VIVO_APP_KEY=

# ==============================
# vivo 通用 OCR
# ==============================
VIVO_OCR_ENABLED=false
# 官方文档给出 HTTP；实现时先对 synthetic 样例验证 HTTPS 是否可用
VIVO_OCR_BASE_URL=http://api-ai.vivo.com.cn
VIVO_OCR_PATH=/ocr/general_recognition
VIVO_OCR_POS=2
# 默认由程序使用 "aigc" + VIVO_APP_ID；如赛事账户需要固定值，可本地覆盖
VIVO_OCR_BUSINESS_ID_OVERRIDE=
VIVO_OCR_TIMEOUT_SECONDS=10

# ==============================
# vivo LLM evidence reranker
# ==============================
VIVO_LLM_ENABLED=false
VIVO_LLM_BASE_URL=https://api-ai.vivo.com.cn/v1
VIVO_LLM_PATH=/chat/completions
VIVO_LLM_MODEL=qwen3.5-plus
VIVO_LLM_REQUEST_ID_QUERY_STYLE=request_id
VIVO_LLM_TEMPERATURE=0.1
VIVO_LLM_MAX_TOKENS=1024
VIVO_LLM_REASONING_EFFORT=minimal
VIVO_LLM_ENABLE_THINKING=false
VIVO_LLM_TIMEOUT_SECONDS=45

# ==============================
# 合成 smoke test
# ==============================
RUN_VIVO_LIVE_SMOKE=false
DEMO_RUNTIME_DIR=runtime
```

`.gitignore` 检查：

```gitignore
.env
.env.*
!.env.example
runtime/
demo-app/backend/runtime/
*.db
*.sqlite
*.sqlite3
*vivo_api_raw_request*
*vivo_api_raw_response*
*external_api_debug*
```

---

# 4. OCR Provider 的精确实现要求

## 4.1 统一接口

如果当前代码已有同类 schema，请适配而不是重复造类型：

```python
class OCRBlock(BaseModel):
    block_id: str
    text: str
    bbox: list[float] | None = None
    polygon: list[list[float]] | None = None
    coordinate_mode: str | None = None   # "relative" / "absolute"
    confidence: float | None = None      # vivo live OCR 当前保持 None

class OCRResult(BaseModel):
    provider: str                        # "vivo_general_ocr"
    provider_label: str                  # "vivo 通用 OCR"
    full_text: str
    blocks: list[OCRBlock]
    angle: int | None = None
    supports_bounding_boxes: bool
    synthetic: bool = True
    warning_messages: list[str] = []
```

## 4.2 请求封装

实现逻辑：

```python
def recognize(image_path: Path, *, synthetic: bool) -> OCRResult:
    assert_external_synthetic_only(synthetic)

    image_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    business_id = (
        settings.vivo_ocr_business_id_override
        or f"aigc{settings.vivo_app_id}"
    )

    headers = {
        "Authorization": f"Bearer {settings.vivo_app_key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    params = {"requestId": request_id}
    data = {
        "image": image_base64,
        "pos": 2,
        "businessid": business_id,
        "sessid": session_id,
    }

    response = http_client.post(
        settings.vivo_ocr_url,
        headers=headers,
        params=params,
        data=data,
        timeout=settings.vivo_ocr_timeout_seconds,
    )
```

注意：

- 不打印 `image_base64`；
- 不打印 `Authorization`；
- 错误日志只记录 `request_id`、HTTP 状态和脱敏后的错误类别；
- 如果官方接口只接受 HTTP，该事实应被 provider status 输出为 warning，而不是隐藏。

## 4.3 响应解析

文档给出了 `pos=1` 的结构；`pos=2` 实际组合结构需通过 synthetic smoke test 固定 fixture 后解析。解析器至少支持：

```json
{
  "result": {
    "OCR": [
      {
        "words": "食欲不振",
        "location": {
          "top_left": {"x": 10, "y": 20},
          "top_right": {"x": 110, "y": 20},
          "down_left": {"x": 10, "y": 50},
          "down_right": {"x": 110, "y": 50}
        }
      }
    ],
    "angle": 0
  }
}
```

转换规则：

```python
polygon = [
    [top_left.x, top_left.y],
    [top_right.x, top_right.y],
    [down_right.x, down_right.y],
    [down_left.x, down_left.y],
]
bbox = [
    min(x for x, y in polygon),
    min(y for x, y in polygon),
    max(x for x, y in polygon),
    max(y for x, y in polygon),
]
```

对于 `pos=2` 坐标相对值：

- Provider 必须保留 `coordinate_mode="relative"`；
- 前端 `EvidenceCanvas` 将相对坐标按图片展示尺寸映射；
- 若 smoke test 发现相对坐标尺度不是 `[0,1]` 而是百分比或固定基准，记录实际转换规则到 `docs/VIVO_API_VERIFICATION.md` 与 fixture 测试中；
- 在未完成坐标尺度验证前，不要将 live 高亮宣称为验收通过。

## 4.4 状态显示

live OCR 结果的 UI 标签：

```text
vivo OCR 识别｜已返回原图位置｜接口未提供识别置信度
```

调用失败回退 sidecar 时：

```text
预置合成 OCR 回放｜用于保持演示流程可运行
```

---

# 5. LLM Provider 的精确实现要求

## 5.1 本阶段不用 Function Calling

使用普通非流式 Chat Completions：

```http
POST https://api-ai.vivo.com.cn/v1/chat/completions?request_id=<uuid>
Authorization: Bearer <AppKey>
Content-Type: application/json
```

若 synthetic smoke test 返回 `1001` 且提示缺少 `requestId`，允许 provider 仅重试一次：

```http
?requestId=<uuid>
```

将最终成功字段写入 `docs/VIVO_API_VERIFICATION.md`，之后固定采用成功字段，不要每次双请求。

## 5.2 请求 payload

推荐 payload：

```json
{
  "model": "qwen3.5-plus",
  "messages": [
    {
      "role": "system",
      "content": "读取 prompts/vivo_evidence_linked_search_system.txt 的内容"
    },
    {
      "role": "user",
      "content": "{\"query\":\"病人最近的材料中是否提到食欲不振？\",\"candidate_segments\":[...]}"
    }
  ],
  "stream": false,
  "temperature": 0.1,
  "max_tokens": 1024,
  "enable_thinking": false
}
```

如果切换为 `Volc-DeepSeek-V3.2`，使用：

```json
{
  "model": "Volc-DeepSeek-V3.2",
  "reasoning_effort": "minimal",
  "stream": false,
  "temperature": 0.1,
  "max_tokens": 1024
}
```

实现中应根据模型名构建 model-specific optional fields，避免给不支持该字段的模型发送无效参数。

## 5.3 LLM System Prompt

保存为：

```text
demo-app/backend/prompts/vivo_evidence_linked_search_system.txt
```

内容：

```text
你是“转诊迹”的证据联查排序模块。输入内容全部来自带有显著标识的合成演示病历材料。

你的任务仅包括：
1. 在给定 candidate_segments 中判断哪些片段与 query 直接相关或存在明确同义表述；
2. 按相关性排序；
3. 为每条选中片段写一句不超出原文的材料归纳。

严格限制：
- 只使用 candidate_segments 的文字，不添加外部医学知识。
- 不输出诊断、风险判断、病因推断、检查建议、用药建议或治疗建议。
- 不声称患者真实存在或不存在某种情况，只能说明“某份材料记载了什么”。
- 每条结果必须返回输入中真实存在的 segment_id。
- evidence_summary 不得表达比 source excerpt 更强的事实。
- 没有明确相关片段时，返回空 items。
- 只输出 JSON，不输出 Markdown、代码块或额外解释。

JSON schema：
{
  "expanded_terms": ["同义检索词"],
  "items": [
    {
      "segment_id": "输入中存在的 segment_id",
      "relevance_level": "direct_mention | synonymous_mention | contextual",
      "evidence_summary": "严格依据原文的一句材料归纳"
    }
  ]
}
```

## 5.4 后端硬校验与安全过滤

LLM 输出不得直接透传至前端。必须：

1. 从 `choices[0].message.content` 取得文本；
2. 去除可能的 Markdown code fence 后解析 JSON；
3. 检查所有 `segment_id` 属于本次候选集合；
4. 检查 `relevance_level` 在枚举范围；
5. 将后端保存的 `source_excerpt`、日期、文档类型、bbox 回填到结果中；
6. 对摘要作边界过滤：若包含“建议治疗”“应检查”“诊断为”“风险”等越界表达，丢弃 LLM 摘要并回退为模板式材料归纳；
7. 解析失败、审核干预、限流或权限失败时，自动使用本地检索排序结果；
8. 前端显示真实模式：`BlueLM 辅助排序` 或 `本地证据检索`。

## 5.5 错误处理

根据文档错误码，加入：

| 场景 | 行为 |
| --- | --- |
| `1001` 参数异常 | 若为 request id 名称不一致，只做一次兼容重试；否则标记 provider 配置错误 |
| `1007` 审核干预 | 不重复调用；转为本地检索，UI 提示“外部排序未启用，已使用本地证据检索” |
| `30001` 无权限/权限到期 | 关闭本次请求 provider，回退本地检索 |
| `30001` rate limit | 有界重试最多 1 次，短延迟后失败则 fallback |
| `2003` 当日用量限制 | 不重试，fallback；完成报告记录额度限制 |
| HTTP/Timeout | 最多 1 次有界重试，之后 fallback |

禁止任何无限重试逻辑。

---

# 6. Provider Status 与完成报告修订

## 6.1 `GET /api/v3/demo/providers/status`

返回中应区分“配置完成”“本地已实际调用通过”“当前结果来自哪种模式”：

```json
{
  "synthetic_only": true,
  "ocr": {
    "configured": true,
    "enabled": true,
    "provider": "vivo_general_ocr",
    "endpoint_scheme": "http",
    "position_mode": "pos=2",
    "supports_bounding_boxes": true,
    "provides_confidence": false,
    "last_synthetic_smoke_test": "passed",
    "warning": "官方文档提供的 OCR endpoint 为 HTTP；仅用于合成演示材料。"
  },
  "llm": {
    "configured": true,
    "enabled": true,
    "provider": "vivo_chat_completions",
    "model": "qwen3.5-plus",
    "request_id_query_style": "request_id",
    "last_synthetic_smoke_test": "passed"
  },
  "fallback_available": true,
  "notice": "外部能力仅处理合成演示材料；系统不生成诊断或治疗建议。"
}
```

若没有真实凭证或未 smoke test：

```json
{
  "last_synthetic_smoke_test": "not_run"
}
```

不得将 mock 单元测试写成 live API 已通过。

## 6.2 完成报告必须包含的真实结论

新增 `docs/DEMO_V0_9_1_API_RESOLVED_COMPLETION_REPORT.md` 或更新已有完成报告，填写：

```markdown
## vivo OCR 接入结果
- 是否完成 adapter：
- 是否用真实凭证对合成样例调用：
- 使用的 endpoint scheme：http / https / 未运行
- pos 参数：2
- 是否返回可渲染位置：
- 是否提供置信度：根据当前文档与响应核验，未提供 / 已发现字段
- fallback 是否可运行：

## vivo LLM 接入结果
- 是否完成 adapter：
- 是否用真实凭证对合成候选片段调用：
- 实际成功模型：
- request id query 字段实际成功值：request_id / requestId / 未运行
- 是否成功解析 grounded JSON：
- API 不可用时本地检索是否可运行：

## 数据安全检查
- 外部调用材料是否全部 synthetic：
- 是否存在真实病历：
- `.env` 是否未追踪：
- AppKey 是否未进入前端 bundle / logs / git：
- runtime/raw response 是否未追踪：
```

---

# 7. 新增/修订测试清单

## 7.1 OCR provider mock 测试

使用伪造响应 fixture，不消耗 API 调用额度：

```text
tests/fixtures/vivo/ocr_pos2_success.json
tests/fixtures/vivo/ocr_error_image.json
tests/fixtures/vivo/ocr_error_recognition.json
```

必须断言：

- 请求 method 为 POST；
- Content-Type 为 `application/x-www-form-urlencoded`；
- query key 为 `requestId`；
- form 中存在 `image`、`pos=2`、`businessid`、`sessid`；
- `Authorization` header 存在但测试日志不泄露假 key；
- response 能解析出 words 和 bbox/polygon；
- `confidence is None`；
- `error_code=1/2` 正确进入 fallback；
- `synthetic=false` 时根本不会发起外部请求。

## 7.2 LLM provider mock 测试

必须断言：

- URL 为 `/v1/chat/completions`；
- Header 为 Bearer key；
- `stream=false`；
- candidates 只包含 Top-K 合成文本片段；
- 请求不包含原图 base64；
- LLM 返回有效 JSON 时绑定正确 segment；
- 返回不存在的 segment_id 被拒绝；
- 输出诊断/治疗建议表达时被过滤或回退；
- 1007/30001/2003/timeout 时本地检索仍可返回关联证据；
- request id 参数兼容重试最多一次。

## 7.3 E2E 展示修订

E2E 流程：

```text
进入“采集新材料”
→ 上传清晰合成病历
→ provider 状态显示 vivo OCR 或透明 fallback
→ OCR 结果进入 DocumentSegment
→ 输入“病人最近的材料中是否提到食欲不振？”
→ 页面显示 BlueLM 辅助排序或本地证据检索标识
→ 点击结果的“查看原图证据”
→ 若该结果来自有坐标 OCR：图片高亮正确片段
→ 页面不显示伪造置信度或诊断建议
```

---

# 8. README / 路演表达修订

README 应加入：

```markdown
## 外部 API 增强演示模式

本项目支持在本地配置 vivo API 凭证后，对带水印的合成演示材料进行增强处理：

- vivo 通用 OCR：识别合成文档文字，并在接口返回位置时支撑原图证据定位；
- vivo Chat Completions：仅对本地检索得到的候选证据片段进行相关性排序与材料归纳。

默认 public 仓库运行模式无需凭证，使用离线合成 fixture 与本地检索 fallback。
本仓库不支持上传或处理真实患者数据。

特别说明：官方 OCR 文档当前提供的调用地址为 HTTP。该外部 OCR 调用仅可用于比赛中的
合成演示数据验证；真实医疗场景接入前，必须具备加密传输、访问控制、审计与合规环境。
```

路演中可以表述：

```text
我们通过 vivo OCR 识别合成病历中的文字和位置，通过 vivo 大模型在可追溯候选片段中
辅助筛选医生关心的相关记录。系统不会把大模型生成内容作为医学结论：医生看到的每条
关联材料，都可回到原始文字与图像位置进行核验。由于本次为公开比赛 Demo，全流程仅
使用带水印的合成材料。
```

---

# 9. 直接发送给正在运行的 Codex 的消息

```text
接口字段已经补齐，请在不推翻现有 v0.9 实现的前提下读取
`docs/PRD_V0_9_1_VIVO_API_RESOLVED_PATCH.md`，并用其中的已核实契约替换原先
“等待官方页面核实”的 placeholder。

已核实事实：
1. OCR：POST `http://api-ai.vivo.com.cn/ocr/general_recognition`；
   Header 为 `Authorization: Bearer AppKey` 与
   `Content-Type: application/x-www-form-urlencoded`；
   query 必填 `requestId=<uuid>`；
   body 必填 `image=<base64>`、`pos`、`businessid`，可选 `sessid`；
   `businessid` 文档写为 `"aigc"+AppId`；
   本项目固定请求 `pos=2`，因为文档明确该模式提供文字和坐标信息并建议使用。
   重要：文档未列出 OCR confidence 字段，因此 live OCR 结果不得伪造 0.91 这类
   置信度；UI 显示“位置由 vivo OCR 返回；接口未提供识别置信度”。
2. OCR 文档给出的 endpoint 是 HTTP 且携带 Bearer AppKey。请先用 synthetic 样例
   测试相同路径 HTTPS 是否可用；若只能用 HTTP，只能用于本次带水印合成材料 Demo，
   并在 README/完成报告中显式记录传输安全限制，绝不上传真实患者材料。
3. LLM：POST `https://api-ai.vivo.com.cn/v1/chat/completions`，
   `Authorization: Bearer AppKey`，OpenAI-compatible Chat Completions。
   可用模型包括 `Volc-DeepSeek-V3.2`、`Doubao-Seed-2.0-mini/lite/pro`、
   `qwen3.5-plus`，模型从 `.env` 配置。
4. LLM 文档的参数表写 `requestId`，但官方 Python/requests 示例均使用
   `request_id`。provider 默认按示例使用 `request_id`；若 synthetic smoke test
   返回缺参错误 1001，只允许兼容重试一次改为 `requestId`，并把最终成功字段写入
   完成报告。
5. 证据联查不使用 Function Calling。请使用非流式 chat completion，让 LLM 仅对
   本地召回后的 Top-K DocumentSegment 做相关性排序与基于原文的一句归纳；
   每条结果必须绑定有效 segment_id。解析失败、限流、审核干预、无权限或内容越界
   时回退本地证据检索。
6. 更新 `.env.example`、`.gitignore`、`docs/VIVO_API_VERIFICATION.md`、
   provider status、mock 测试、synthetic-only smoke test 和完成报告。
   public 仓库继续只包含合成数据，不提交 key、.env、runtime、raw response 或任何
   真实病例。
```

---

# 10. 本补丁的完成标准

- [ ] vivo OCR endpoint、headers、query、form body 已按已核实文档实现；
- [ ] OCR 固定 `pos=2` 并能将返回位置转换为 evidence overlay；
- [ ] live OCR 不再展示虚构置信度；
- [ ] HTTP endpoint 的 synthetic-only 与安全披露已落入 UI/README/完成报告；
- [ ] vivo LLM endpoint 与 OpenAI-compatible 调用已实现；
- [ ] request id 的文档不一致已通过 synthetic smoke test 确定或被明确记录为未运行；
- [ ] 不引入 Function Calling 造成额外实现风险；
- [ ] LLM 仅在候选 segment 中排序/归纳并严格绑定证据；
- [ ] provider 失败能透明 fallback；
- [ ] 自动测试、E2E 与 public 仓库安全检查完成并记录真实结果。
