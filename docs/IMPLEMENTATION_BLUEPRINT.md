# 前后端分离实现蓝图

## 推荐目录

如当前仓库尚未搭建工程，可采用：

```text
zgcHack/
├─ AGENTS.md
├─ .codex/skills/
├─ apps/
│  ├─ web/                         # React/Vite 前端
│  └─ api/                         # FastAPI 后端
├─ demo-data/
│  ├─ cases/
│  └─ assets/
├─ docs/
└─ reference/
```

若实际仓库已有前端框架，则保留既有结构，只迁移硬编码数据来源、增加 backend 与测试，不因目录偏好大规模重写。

## 数据流

```text
合成文件上传按钮
  -> POST /api/v1/demo/uploads
  -> job completed + generated_case_id
  -> GET /cases/{id}/timeline
  -> 时间轴渲染
  -> 点击 node/material
  -> GET /materials/{material_id}
  -> 原图 + OCR + evidence anchor 核验视图
```

## Frontend 最小组件拆分

- `TransferCaseHeader`：患者与转院上下文、安全提示。
- `TimelineFilters`：异常/材料类型/转院相关筛选。
- `HorizontalTimeline`：时间轴及节点。
- `TimelineNodeCard`：缩略图、日期、概要、标签。
- `NodeDetailPanel`：当前节点结构化详情。
- `EvidenceModal`：合成原图、定位、OCR、置信度。
- `UploadSimulationPanel`：处理流程展示。
- `RequestState`：loading/error/empty/low confidence。

## Backend 最小模块拆分

- fixtures loader + schema validation；
- case/timeline/material query routes；
- upload job simulation route；
- assets static serving；
- CORS/local config；
- route and integrity tests。

## 保留现有原型的关键设计

现有 HTML 已将时间轴、详情侧栏、证据弹窗和六个心内科节点具象化。实现阶段应将其作为视觉基线，优先替换数据层和补齐状态交互，而非重新发明页面结构。
