import { AlertTriangle, CheckCircle2, FileSearch, RefreshCw, Upload, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  assetUrl,
  createUploadJob,
  getCases,
  getJob,
  getMaterial,
  getTimeline,
} from "./api";
import { evidenceStatusText, filterNodes, type NodeFilter, verificationStatusLabel } from "./model";
import type { CaseSummary, EvidenceAnchor, Material, TimelineNode, TimelineResponse } from "./types";

const SAFETY_NOTICE = "合成演示数据，仅用于材料整理演示，不构成诊断或治疗建议。";

interface EvidenceSelection {
  material: Material;
  anchor?: EvidenceAnchor;
}

export function App() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [notice, setNotice] = useState(SAFETY_NOTICE);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [activeNodeId, setActiveNodeId] = useState("");
  const [filter, setFilter] = useState<NodeFilter>({ kind: "all" });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [evidence, setEvidence] = useState<EvidenceSelection | null>(null);
  const [isEvidenceLoading, setIsEvidenceLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("等待选择合成演示材料");
  const [selectedFileNames, setSelectedFileNames] = useState<string[]>([
    "合成转院材料-1.pdf",
    "合成检验截图-2.jpg",
  ]);

  useEffect(() => {
    void loadCaseList();
  }, []);

  async function loadCaseList() {
    setIsLoading(true);
    setError("");
    try {
      const payload = await getCases();
      setCases(payload.cases);
      setNotice(payload.notice);
      const firstCaseId = selectedCaseId || payload.cases[0]?.case_id || "";
      setSelectedCaseId(firstCaseId);
      if (firstCaseId) {
        await loadTimeline(firstCaseId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法加载病例列表。");
      setTimeline(null);
    } finally {
      setIsLoading(false);
    }
  }

  async function loadTimeline(caseId: string) {
    setIsLoading(true);
    setError("");
    try {
      const payload = await getTimeline(caseId);
      setTimeline(payload);
      setSelectedCaseId(caseId);
      setNotice(payload.notice);
      setFilter({ kind: "all" });
      setActiveNodeId(payload.timeline_nodes[0]?.node_id ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法加载时间轴。");
      setTimeline(null);
    } finally {
      setIsLoading(false);
    }
  }

  const filteredNodes = useMemo(
    () => filterNodes(timeline?.timeline_nodes ?? [], filter),
    [filter, timeline],
  );

  const activeNode = useMemo(() => {
    if (!timeline) return undefined;
    return (
      timeline.timeline_nodes.find((node) => node.node_id === activeNodeId) ??
      filteredNodes[0] ??
      timeline.timeline_nodes[0]
    );
  }, [activeNodeId, filteredNodes, timeline]);

  async function openEvidence(materialId: string, anchor?: EvidenceAnchor) {
    if (!timeline) return;
    setIsEvidenceLoading(true);
    try {
      const material = await getMaterial(timeline.case_id, materialId);
      setEvidence({ material, anchor });
    } finally {
      setIsEvidenceLoading(false);
    }
  }

  async function handleUpload() {
    if (!selectedCaseId) return;
    setUploadStatus("正在创建合成处理任务...");
    try {
      const job = await createUploadJob(selectedCaseId, selectedFileNames);
      setUploadStatus(`任务 ${job.job_id} 已创建，正在读取任务状态...`);
      const completed = await getJob(job.job_id);
      setUploadStatus(`${completed.message} 已进入 ${completed.generated_case_id}`);
      await loadTimeline(completed.generated_case_id);
    } catch (err) {
      setUploadStatus(err instanceof Error ? `上传模拟失败：${err.message}` : "上传模拟失败。");
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="title-block">
          <p className="eyebrow">zgcHack Demo</p>
          <h1>转院病历时间轴</h1>
          <p className="subtitle">按日期整理外院合成材料，保留 OCR、字段和原图定位。</p>
          <div className="notice" role="note">
            <AlertTriangle size={16} />
            <span>{notice}</span>
          </div>
        </div>

        <div className="header-actions">
          <label className="control-label" htmlFor="case-select">
            演示病例
          </label>
          <select
            id="case-select"
            value={selectedCaseId}
            onChange={(event) => void loadTimeline(event.target.value)}
            aria-label="选择演示病例"
          >
            {cases.map((item) => (
              <option key={item.case_id} value={item.case_id}>
                {item.patient_display}｜{item.destination_department}
              </option>
            ))}
          </select>
          <button className="icon-button primary" type="button" onClick={() => void handleUpload()}>
            <Upload size={17} />
            模拟上传
          </button>
        </div>
      </header>

      <main className="workspace">
        <section className="main-pane" aria-label="时间轴工作区">
          {timeline && <CaseOverview timeline={timeline} />}
          <UploadStrip
            fileNames={selectedFileNames}
            status={uploadStatus}
            onFilesChange={setSelectedFileNames}
          />
          <FilterBar
            timeline={timeline}
            filter={filter}
            onFilter={setFilter}
            onRetry={() => void loadCaseList()}
          />

          {isLoading && <LoadingState />}
          {!isLoading && error && <ErrorState message={error} onRetry={() => void loadCaseList()} />}
          {!isLoading && !error && timeline && (
            <TimelineRail
              timeline={timeline}
              nodes={filteredNodes}
              activeNodeId={activeNode?.node_id ?? ""}
              onSelect={setActiveNodeId}
              onOpenEvidence={openEvidence}
            />
          )}
        </section>

        <aside className="detail-pane" aria-label="节点详情与证据追溯">
          <DetailPanel
            timeline={timeline}
            node={activeNode}
            onOpenEvidence={openEvidence}
            evidenceLoading={isEvidenceLoading}
          />
        </aside>
      </main>

      {evidence && <EvidenceModal selection={evidence} onClose={() => setEvidence(null)} />}
    </div>
  );
}

function CaseOverview({ timeline }: { timeline: TimelineResponse }) {
  const abnormalCount = timeline.timeline_nodes.filter((node) => node.has_abnormal_flag).length;
  const items = [
    ["患者", `${timeline.patient.display_name}，${timeline.patient.sex}，${timeline.patient.age_display}`],
    ["转院路径", `${timeline.transfer.origin_hospital} → ${timeline.transfer.destination_hospital}`],
    ["目标科室", timeline.transfer.destination_department],
    ["材料覆盖", `${timeline.transfer.coverage}｜${timeline.timeline_nodes.length} 个节点`],
    ["异常字段待核验", `${abnormalCount} 个节点含标记字段`],
  ];
  return (
    <section className="case-overview" aria-label="转院摘要">
      {items.map(([label, value]) => (
        <div className="summary-tile" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </section>
  );
}

function UploadStrip({
  fileNames,
  status,
  onFilesChange,
}: {
  fileNames: string[];
  status: string;
  onFilesChange: (names: string[]) => void;
}) {
  return (
    <section className="upload-strip" aria-label="模拟上传处理">
      <div>
        <div className="section-kicker">模拟上传</div>
        <p>仅发送合成演示文件名，不读取或上传文件内容。</p>
      </div>
      <label className="file-picker">
        <FileSearch size={17} />
        选择演示文件名
        <input
          type="file"
          multiple
          onChange={(event) => {
            const names = Array.from(event.target.files ?? []).map((file) => file.name);
            onFilesChange(names.length ? names : ["合成转院材料-1.pdf"]);
          }}
        />
      </label>
      <div className="upload-meta">
        <span>{fileNames.join("、")}</span>
        <strong>{status}</strong>
      </div>
    </section>
  );
}

function FilterBar({
  timeline,
  filter,
  onFilter,
  onRetry,
}: {
  timeline: TimelineResponse | null;
  filter: NodeFilter;
  onFilter: (filter: NodeFilter) => void;
  onRetry: () => void;
}) {
  return (
    <section className="filter-bar" aria-label="时间轴筛选">
      <button
        className={filter.kind === "all" ? "filter active" : "filter"}
        type="button"
        onClick={() => onFilter({ kind: "all" })}
      >
        全部节点
      </button>
      <button
        className={filter.kind === "abnormal" ? "filter active" : "filter"}
        type="button"
        onClick={() => onFilter({ kind: "abnormal" })}
      >
        只看异常
      </button>
      <button
        className={filter.kind === "transfer" ? "filter active" : "filter"}
        type="button"
        onClick={() => onFilter({ kind: "transfer" })}
      >
        与转院原因相关
      </button>
      <select
        className="document-select"
        value={filter.kind === "document_type" ? filter.value : ""}
        onChange={(event) => {
          if (event.target.value) onFilter({ kind: "document_type", value: event.target.value });
        }}
        aria-label="按材料类型筛选"
      >
        <option value="">材料类型</option>
        {timeline?.available_filters.document_types.map((type) => (
          <option key={type} value={type}>
            {type}
          </option>
        ))}
      </select>
      <button className="filter" type="button" onClick={() => onFilter({ kind: "empty_demo" })}>
        空结果演示
      </button>
      <button className="retry-link" type="button" onClick={onRetry}>
        <RefreshCw size={16} />
        重试加载
      </button>
    </section>
  );
}

function TimelineRail({
  timeline,
  nodes,
  activeNodeId,
  onSelect,
  onOpenEvidence,
}: {
  timeline: TimelineResponse;
  nodes: TimelineNode[];
  activeNodeId: string;
  onSelect: (nodeId: string) => void;
  onOpenEvidence: (materialId: string, anchor?: EvidenceAnchor) => Promise<void>;
}) {
  if (!nodes.length) {
    return (
      <div className="empty-state" role="status">
        <FileSearch size={28} />
        <strong>当前筛选下没有时间轴节点</strong>
        <span>可切回全部节点，或选择其他合成病例继续演示。</span>
      </div>
    );
  }
  return (
    <section className="timeline-wrap" aria-label="横向病历时间轴">
      <div className="timeline-rail">
        {nodes.map((node) => {
          const firstMaterial = timeline.materials[node.materials[0]];
          const firstEvidence = node.evidence_anchors[0];
          return (
            <article className={node.node_id === activeNodeId ? "timeline-node active" : "timeline-node"} key={node.node_id}>
              <button className="thumb-button" type="button" onClick={() => void onOpenEvidence(firstMaterial.material_id, firstEvidence)}>
                <img src={assetUrl(firstMaterial.image_url)} alt={`${firstMaterial.title}缩略图`} />
              </button>
              <button className="node-date" type="button" onClick={() => onSelect(node.node_id)} aria-pressed={node.node_id === activeNodeId}>
                <span className="axis-dot" />
                <span>{node.date}</span>
              </button>
              <button className="node-card" type="button" onClick={() => onSelect(node.node_id)}>
                <strong>{node.headline}</strong>
                <span>{node.summary}</span>
                <span className="tag-row">
                  {node.tags.map((tag) => (
                    <span className={`tag ${tag.level}`} key={`${node.node_id}-${tag.label}`}>
                      {tag.label}
                    </span>
                  ))}
                </span>
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function DetailPanel({
  timeline,
  node,
  onOpenEvidence,
  evidenceLoading,
}: {
  timeline: TimelineResponse | null;
  node?: TimelineNode;
  onOpenEvidence: (materialId: string, anchor?: EvidenceAnchor) => Promise<void>;
  evidenceLoading: boolean;
}) {
  if (!timeline || !node) {
    return <div className="detail-empty">请选择时间轴节点。</div>;
  }
  const materials = node.materials.map((id) => timeline.materials[id]).filter(Boolean);
  const evidenceByField = new Map(node.evidence_anchors.map((anchor) => [anchor.field_key, anchor]));
  return (
    <div className="detail-content">
      <div className="detail-head">
        <span>{node.date}</span>
        <h2>{node.headline}</h2>
        <p>{node.hospital_department}｜{node.document_type}</p>
      </div>

      <div className="material-stack">
        {materials.map((material) => (
          <button
            className="material-preview"
            type="button"
            key={material.material_id}
            onClick={() => void onOpenEvidence(material.material_id, material.evidence_anchors[0])}
          >
            <img src={assetUrl(material.image_url)} alt={`${material.title}预览`} />
            <span>{material.title}</span>
          </button>
        ))}
      </div>

      <section className="field-list" aria-label="结构化字段">
        {Object.entries(node.structured_fields).map(([key, value]) => {
          const anchor = evidenceByField.get(key);
          return (
            <button
              className={anchor?.confidence && anchor.confidence < 0.85 ? "field-item low" : "field-item"}
              type="button"
              key={key}
              onClick={() => anchor && void onOpenEvidence(anchor.material_id, anchor)}
            >
              <span>{key}</span>
              <strong>{value}</strong>
              {anchor && (
                <em>
                  {evidenceStatusText(anchor.confidence)}｜OCR {Math.round(anchor.confidence * 100)}%
                </em>
              )}
            </button>
          );
        })}
      </section>

      <section className="evidence-list" aria-label="证据定位">
        <h3>证据追溯</h3>
        {node.evidence_anchors.map((anchor) => (
          <button className="evidence-item" type="button" key={anchor.anchor_id} onClick={() => void onOpenEvidence(anchor.material_id, anchor)}>
            <FileSearch size={16} />
            <span>{anchor.display_value}</span>
            <small>
              {anchor.page_or_image}｜{verificationStatusLabel(anchor.verification_status)}
            </small>
          </button>
        ))}
        {evidenceLoading && <span className="loading-inline">正在打开证据材料...</span>}
      </section>

      <section className="ocr-box">
        <h3>OCR 片段</h3>
        <p>{node.ocr_excerpt}</p>
      </section>

      <section className="missing-box">
        <h3>材料完整性提示</h3>
        {timeline.missing_material_reminders.map((item) => (
          <p key={item}>{item}</p>
        ))}
      </section>
    </div>
  );
}

function EvidenceModal({ selection, onClose }: { selection: EvidenceSelection; onClose: () => void }) {
  const anchor = selection.anchor;
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="证据材料视图">
      <div className="evidence-modal">
        <button className="close-button" type="button" onClick={onClose} aria-label="关闭证据视图">
          <X size={20} />
        </button>
        <div className="modal-head">
          <span>原图定位</span>
          <h2>{selection.material.title}</h2>
          <p>{SAFETY_NOTICE}</p>
        </div>
        <div className="modal-grid">
          <div className="source-image-wrap">
            <img src={assetUrl(selection.material.image_url)} alt={`${selection.material.title}合成原始材料`} />
            {anchor && <div className="locator-highlight">定位：{anchor.locator_text}</div>}
          </div>
          <div className="source-detail">
            {anchor ? (
              <>
                <div className={anchor.confidence < 0.85 ? "confidence low" : "confidence"}>
                  <CheckCircle2 size={16} />
                  <span>
                    OCR 置信度 {Math.round(anchor.confidence * 100)}%｜{evidenceStatusText(anchor.confidence)}
                  </span>
                </div>
                <dl>
                  <dt>字段</dt>
                  <dd>{anchor.field_key}</dd>
                  <dt>提取值</dt>
                  <dd>{anchor.display_value}</dd>
                  <dt>位置</dt>
                  <dd>{anchor.page_or_image}</dd>
                  <dt>核验状态</dt>
                  <dd>{verificationStatusLabel(anchor.verification_status)}</dd>
                </dl>
              </>
            ) : (
              <p className="muted-text">该材料没有绑定关键字段证据。</p>
            )}
            <div className="ocr-box modal-ocr">
              <h3>OCR 全文</h3>
              <p>{selection.material.ocr_text}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="loading-state" role="status">
      <span />
      <span />
      <span />
      <strong>正在加载合成病例时间轴...</strong>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="error-state" role="alert">
      <AlertTriangle size={28} />
      <strong>API 加载失败</strong>
      <span>{message}</span>
      <button className="icon-button primary" type="button" onClick={onRetry}>
        <RefreshCw size={17} />
        重新加载
      </button>
    </div>
  );
}
