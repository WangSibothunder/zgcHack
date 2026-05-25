import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  ClipboardList,
  FileSearch,
  RefreshCw,
  Upload,
  X,
} from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  assetUrl,
  createIngestionJob,
  createUploadJob,
  getCases,
  getJob,
  getMaterial,
  getPreConsultSummary,
  getTimeline,
  reviewEvidence,
  searchEvidence,
} from "./api";
import {
  evidenceStatusText,
  filterNodes,
  qualityStatusLabel,
  type NodeFilter,
  verificationStatusLabel,
} from "./model";
import type {
  CaseSummary,
  CaseSummaryV2,
  EvidenceAnchor,
  EvidenceSearchItem,
  EvidenceSearchResponse,
  IngestionJob,
  Material,
  ReviewAction,
  TimelineNode,
  TimelineResponse,
} from "./types";

const SAFETY_NOTICE = "合成演示数据，仅用于材料整理演示，不构成诊断或治疗建议。";

type ActiveTab = "timeline" | "capture" | "summary";

interface EvidenceSelection {
  material: Material;
  anchor?: EvidenceAnchor;
}

export function App() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [notice, setNotice] = useState(SAFETY_NOTICE);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [summary, setSummary] = useState<CaseSummaryV2 | null>(null);
  const [activeNodeId, setActiveNodeId] = useState("");
  const [filter, setFilter] = useState<NodeFilter>({ kind: "all" });
  const [activeTab, setActiveTab] = useState<ActiveTab>("timeline");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [evidence, setEvidence] = useState<EvidenceSelection | null>(null);
  const [isEvidenceLoading, setIsEvidenceLoading] = useState(false);
  const selectedFileNames = ["合成转院材料-1.pdf", "合成检验截图-2.jpg"];
  const [ingestionJob, setIngestionJob] = useState<IngestionJob | null>(null);
  const [captureMessage, setCaptureMessage] = useState("");
  const [searchQuestion, setSearchQuestion] = useState("病人最近的材料中是否提到食欲不振？");
  const [searchResult, setSearchResult] = useState<EvidenceSearchResponse | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [relatedResult, setRelatedResult] = useState<EvidenceSearchResponse | null>(null);
  const [relatedLoadingKey, setRelatedLoadingKey] = useState("");

  useEffect(() => {
    document.title = "历刻｜转院病历重建系统 Demo";
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

  async function loadTimeline(caseId: string, keepFilter = false) {
    setIsLoading(true);
    setError("");
    try {
      const payload = await getTimeline(caseId);
      setTimeline(payload);
      setSelectedCaseId(caseId);
      setNotice(payload.notice);
      if (!keepFilter) setFilter({ kind: "all" });
      setActiveNodeId(payload.timeline_nodes[0]?.node_id ?? "");
      await refreshSummary(caseId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法加载时间轴。");
      setTimeline(null);
    } finally {
      setIsLoading(false);
    }
  }

  async function refreshSummary(caseId = selectedCaseId) {
    if (!caseId) return;
    try {
      setSummary(await getPreConsultSummary(caseId));
    } catch {
      setSummary(null);
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
      const latestAnchor =
        anchor && material.evidence_anchors.find((item) => item.anchor_id === anchor.anchor_id);
      setEvidence({ material, anchor: latestAnchor ?? anchor });
    } finally {
      setIsEvidenceLoading(false);
    }
  }

  async function openSearchResult(item: EvidenceSearchItem) {
    if (!timeline) return;
    setActiveTab("timeline");
    setActiveNodeId(item.node_id);
    window.requestAnimationFrame(() => {
      document.querySelector(`[data-node-id="${item.node_id}"]`)?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
    });
    const material = await getMaterial(timeline.case_id, item.material_id);
    const anchor = material.evidence_anchors.find((candidate) => candidate.anchor_id === item.anchor_id) ?? material.evidence_anchors[0];
    setEvidence({ material, anchor });
  }

  async function handleEvidenceQuestion() {
    if (!selectedCaseId || !searchQuestion.trim()) return;
    setSearchLoading(true);
    setSearchError("");
    try {
      setSearchResult(
        await searchEvidence({
          case_id: selectedCaseId,
          trigger_type: "question",
          question: searchQuestion,
          top_k: 5,
        }),
      );
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "证据联查失败。");
    } finally {
      setSearchLoading(false);
    }
  }

  async function handleRelatedSearch(anchor: EvidenceAnchor) {
    if (!selectedCaseId) return;
    setRelatedLoadingKey(anchor.anchor_id);
    try {
      setRelatedResult(
        await searchEvidence({
          case_id: selectedCaseId,
          trigger_type: "field",
          selected_material_id: anchor.material_id,
          selected_text: anchor.display_value,
          top_k: 3,
        }),
      );
    } catch (err) {
      setRelatedResult({
        query_id: "local-error",
        case_id: selectedCaseId,
        answer_mode: "evidence_only",
        query_display: "相关记录",
        retrieval_terms: [],
        result_statement: err instanceof Error ? err.message : "关联记录加载失败。",
        items: [],
        not_found_note: "可稍后重试，当前页面不会生成诊断或治疗建议。",
        llm_mode: "unavailable_fallback",
        notice: SAFETY_NOTICE,
        synthetic: true,
      });
    } finally {
      setRelatedLoadingKey("");
    }
  }

  async function handleReview(anchor: EvidenceAnchor, action: ReviewAction, correctedValue?: string, note?: string) {
    await reviewEvidence(anchor.anchor_id, {
      action,
      corrected_value: correctedValue,
      note,
    });
    await loadTimeline(selectedCaseId, true);
    if (evidence) {
      const material = await getMaterial(selectedCaseId, evidence.material.material_id);
      setEvidence({
        material,
        anchor: material.evidence_anchors.find((item) => item.anchor_id === anchor.anchor_id),
      });
    }
    await refreshSummary(selectedCaseId);
  }

  async function handleUpload() {
    if (!selectedCaseId) return;
    try {
      const job = await createUploadJob(selectedCaseId, selectedFileNames);
      const completed = await getJob(job.job_id);
      await loadTimeline(completed.generated_case_id);
      setCaptureMessage(`${completed.message} 已进入 ${completed.generated_case_id}`);
    } catch (err) {
      setCaptureMessage(err instanceof Error ? `上传模拟失败：${err.message}` : "上传模拟失败。");
    }
  }

  async function handleIngestion(files: File[], source: "upload" | "camera") {
    if (!selectedCaseId) return;
    setCaptureMessage("正在上传合成材料并进行质量检测...");
    try {
      const job = await createIngestionJob(files, selectedCaseId, source);
      setIngestionJob(job);
      setCaptureMessage(job.message);
      if (job.status === "timeline_generated") {
        await loadTimeline(job.generated_case_id, true);
        setActiveTab("timeline");
      }
    } catch (err) {
      setCaptureMessage(err instanceof Error ? err.message : "合成材料处理失败。");
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-lockup">
          <div className="brand-logo-panel" aria-hidden="true">
            <img className="brand-logo" src={assetUrl("/assets/logo.png")} alt="" />
          </div>
          <div className="title-block">
            <h1 className="sr-only">历刻</h1>
            <p className="brand-slogan">让天下没有难看的病</p>
            <p className="subtitle">把散落病历，连成可核验的转院时间轴。</p>
          </div>
        </div>

        <div className="header-actions">
          <div className="safety-badge" role="note" title={notice}>
            <AlertTriangle size={14} />
            <span>合成演示｜非诊断</span>
          </div>
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
          <button className="icon-button primary" type="button" onClick={() => setActiveTab("capture")}>
            <Upload size={17} />
            采集材料
          </button>
          <button
            className="icon-button"
            type="button"
            onClick={() => {
              setActiveTab("summary");
              void refreshSummary();
            }}
          >
            <ClipboardList size={17} />
            摘要
          </button>
          <button className="icon-button subtle-action" type="button" onClick={() => void handleUpload()}>
            <Upload size={17} />
            模拟上传
          </button>
        </div>
      </header>

      <nav className="top-tabs" aria-label="历刻工作区">
        <TabButton active={activeTab === "timeline"} onClick={() => setActiveTab("timeline")} icon={<FileSearch size={17} />}>
          医生时间轴
        </TabButton>
        <TabButton active={activeTab === "capture"} onClick={() => setActiveTab("capture")} icon={<Camera size={17} />}>
          采集新材料
        </TabButton>
        <TabButton
          active={activeTab === "summary"}
          onClick={() => {
            setActiveTab("summary");
            void refreshSummary();
          }}
          icon={<ClipboardList size={17} />}
        >
          接诊前摘要
        </TabButton>
      </nav>

      {activeTab === "capture" ? (
        <CaptureWorkbench
          cases={cases}
          selectedCaseId={selectedCaseId}
          onCaseChange={(caseId) => void loadTimeline(caseId)}
          job={ingestionJob}
          message={captureMessage}
          onProcess={handleIngestion}
        />
      ) : activeTab === "summary" ? (
        <PreConsultSummary summary={summary} onRefresh={() => void refreshSummary()} />
      ) : (
        <TimelineWorkspace
          timeline={timeline}
          activeNode={activeNode}
          filteredNodes={filteredNodes}
          activeNodeId={activeNode?.node_id ?? ""}
          filter={filter}
          isLoading={isLoading}
          error={error}
          uploadMessage={captureMessage}
          onFilter={setFilter}
          onRetry={() => void loadCaseList()}
          onSelect={setActiveNodeId}
          onOpenEvidence={openEvidence}
          onOpenSearchResult={openSearchResult}
          searchQuestion={searchQuestion}
          searchResult={searchResult}
          searchLoading={searchLoading}
          searchError={searchError}
          onSearchQuestionChange={setSearchQuestion}
          onSearchQuestion={handleEvidenceQuestion}
          relatedResult={relatedResult}
          relatedLoadingKey={relatedLoadingKey}
          onRelatedSearch={handleRelatedSearch}
          evidenceLoading={isEvidenceLoading}
        />
      )}

      {evidence && (
        <EvidenceModal
          selection={evidence}
          onClose={() => setEvidence(null)}
          onReview={(anchor, action, correctedValue, note) => void handleReview(anchor, action, correctedValue, note)}
        />
      )}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <button className={active ? "tab-button active" : "tab-button"} type="button" onClick={onClick}>
      {icon}
      {children}
    </button>
  );
}

function TimelineWorkspace({
  timeline,
  activeNode,
  filteredNodes,
  activeNodeId,
  filter,
  isLoading,
  error,
  uploadMessage,
  onFilter,
  onRetry,
  onSelect,
  onOpenEvidence,
  onOpenSearchResult,
  searchQuestion,
  searchResult,
  searchLoading,
  searchError,
  onSearchQuestionChange,
  onSearchQuestion,
  relatedResult,
  relatedLoadingKey,
  onRelatedSearch,
  evidenceLoading,
}: {
  timeline: TimelineResponse | null;
  activeNode?: TimelineNode;
  filteredNodes: TimelineNode[];
  activeNodeId: string;
  filter: NodeFilter;
  isLoading: boolean;
  error: string;
  uploadMessage: string;
  onFilter: (filter: NodeFilter) => void;
  onRetry: () => void;
  onSelect: (nodeId: string) => void;
  onOpenEvidence: (materialId: string, anchor?: EvidenceAnchor) => Promise<void>;
  onOpenSearchResult: (item: EvidenceSearchItem) => Promise<void>;
  searchQuestion: string;
  searchResult: EvidenceSearchResponse | null;
  searchLoading: boolean;
  searchError: string;
  onSearchQuestionChange: (value: string) => void;
  onSearchQuestion: () => Promise<void>;
  relatedResult: EvidenceSearchResponse | null;
  relatedLoadingKey: string;
  onRelatedSearch: (anchor: EvidenceAnchor) => Promise<void>;
  evidenceLoading: boolean;
}) {
  return (
    <main className="workspace">
      <section className="main-pane" aria-label="时间轴工作区">
        {timeline && <CaseOverview timeline={timeline} />}
        {timeline && (
          <EvidenceSearchPanel
            question={searchQuestion}
            result={searchResult}
            isLoading={searchLoading}
            error={searchError}
            onQuestionChange={onSearchQuestionChange}
            onSearch={onSearchQuestion}
          />
        )}
        <FilterBar timeline={timeline} filter={filter} onFilter={onFilter} onRetry={onRetry} />
        {uploadMessage && <div className="inline-success">{uploadMessage}</div>}

        {isLoading && <LoadingState />}
        {!isLoading && error && <ErrorState message={error} onRetry={onRetry} />}
        {!isLoading && !error && timeline && (
          <>
            <TimelineRail
              timeline={timeline}
              nodes={filteredNodes}
              activeNodeId={activeNodeId}
              onSelect={onSelect}
              onOpenEvidence={onOpenEvidence}
            />
            {searchResult && <EvidenceSearchResults result={searchResult} onOpenResult={onOpenSearchResult} />}
          </>
        )}
      </section>

      <aside className="detail-pane" aria-label="节点详情与证据追溯">
        <DetailPanel
          timeline={timeline}
          node={activeNode}
          onOpenEvidence={onOpenEvidence}
          onOpenSearchResult={onOpenSearchResult}
          relatedResult={relatedResult}
          relatedLoadingKey={relatedLoadingKey}
          onRelatedSearch={onRelatedSearch}
          evidenceLoading={evidenceLoading}
        />
      </aside>
    </main>
  );
}

function CaseOverview({ timeline }: { timeline: TimelineResponse }) {
  const abnormalCount = timeline.timeline_nodes.filter((node) => node.has_abnormal_flag).length;
  const liveCount = Object.values(timeline.materials).filter((material) => material.processing_source === "现场合成材料处理").length;
  return (
    <section className="case-overview" aria-label="转院摘要">
      <div className="patient-identity">
        <span>当前病例</span>
        <strong>{timeline.patient.display_name}</strong>
        <small>{timeline.patient.sex}，{timeline.patient.age_display}</small>
      </div>
      <div className="transfer-context">
        <div>
          <span>转院路径</span>
          <strong>{timeline.transfer.origin_hospital} → {timeline.transfer.destination_hospital}</strong>
        </div>
        <div>
          <span>目标科室</span>
          <strong>{timeline.transfer.destination_department}</strong>
        </div>
        <div className="overview-status">
          <span>材料覆盖：{timeline.transfer.coverage}</span>
          <span>{timeline.timeline_nodes.length} 个节点</span>
          <span>待核验字段 {abnormalCount} 项</span>
          <span>现场新增 {liveCount} 份</span>
        </div>
      </div>
    </section>
  );
}

function EvidenceSearchPanel({
  question,
  result,
  isLoading,
  error,
  onQuestionChange,
  onSearch,
}: {
  question: string;
  result: EvidenceSearchResponse | null;
  isLoading: boolean;
  error: string;
  onQuestionChange: (value: string) => void;
  onSearch: () => Promise<void>;
}) {
  return (
    <section className="evidence-search-panel" aria-label="证据联查">
      <div className="search-head">
        <div>
          <div className="section-kicker">证据联查</div>
          <p>系统仅查找与归纳已上传材料中的相关证据，不生成诊断或治疗建议。</p>
        </div>
        <span className="provider-pill">{result?.llm_mode === "mock" ? "本地检索模式" : result ? "外部 provider 回退" : "待检索"}</span>
      </div>
      <div className="search-row">
        <input
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") void onSearch();
          }}
          aria-label="输入证据联查问题"
        />
        <button className="icon-button primary" type="button" disabled={isLoading || !question.trim()} onClick={() => void onSearch()}>
          <FileSearch size={17} />
          {isLoading ? "查找中" : "查找相关记录"}
        </button>
      </div>
      {error && <div className="inline-warning">{error}</div>}
      {result && <p className="search-inline-result">{result.result_statement}</p>}
    </section>
  );
}

function EvidenceSearchResults({
  result,
  onOpenResult,
}: {
  result: EvidenceSearchResponse;
  onOpenResult: (item: EvidenceSearchItem) => Promise<void>;
}) {
  return (
    <section className="search-results" aria-live="polite">
      <div className="result-summary">
        <div>
          <span>证据联查结果</span>
          <strong>{result.result_statement}</strong>
        </div>
        <small>{result.retrieval_terms.length ? `检索词：${result.retrieval_terms.join(" / ")}` : result.query_display}</small>
      </div>
      <p className="muted-text">{result.notice}</p>
      {result.not_found_note && <p className="muted-text">{result.not_found_note}</p>}
      {result.items.map((item) => (
        <EvidenceResultCard item={item} key={item.segment_id} onOpenResult={onOpenResult} />
      ))}
    </section>
  );
}

function EvidenceResultCard({
  item,
  onOpenResult,
  compact = false,
}: {
  item: EvidenceSearchItem;
  onOpenResult: (item: EvidenceSearchItem) => Promise<void>;
  compact?: boolean;
}) {
  return (
    <article className={compact ? "evidence-result compact" : "evidence-result"}>
      <div className="result-title">
        <strong>
          {item.document_date ?? "日期待确认"}｜{item.document_type}
          {item.department ? `｜${item.department}` : ""}
        </strong>
        <span>{item.relevance_label}</span>
      </div>
      <p className="source-excerpt">“{item.source_excerpt}”</p>
      <p>材料归纳：{item.evidence_summary}</p>
      <div className="result-actions">
        <small>
          OCR {Math.round(item.ocr_confidence * 100)}%｜{item.ranking_source === "keyword+mock_rerank" ? "本地检索模式" : "回退检索"}
        </small>
        <button className="retry-link" type="button" onClick={() => void onOpenResult(item)}>
          查看原图证据
        </button>
      </div>
    </article>
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
      <button className={filter.kind === "all" ? "filter active" : "filter"} type="button" onClick={() => onFilter({ kind: "all" })}>
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
      <div className="timeline-section-head">
        <div>
          <h2>病程时间轴</h2>
          <p>{nodes.length} 个时间节点 · 选择节点查看事件说明、证据链与原始材料</p>
        </div>
        <span>横向浏览完整时间线</span>
      </div>
      <div className="timeline-axis" aria-label="日期轴">
        {nodes.map((node) => (
          <button
            className={node.node_id === activeNodeId ? "axis-date active" : "axis-date"}
            type="button"
            key={`axis-${node.node_id}`}
            onClick={() => onSelect(node.node_id)}
            aria-pressed={node.node_id === activeNodeId}
            aria-label={node.date}
          >
            <span className={node.has_abnormal_flag ? "axis-dot warning-dot" : "axis-dot"} />
            <span>{node.date}</span>
            {node.node_id === activeNodeId && <em aria-hidden="true">当前选中</em>}
          </button>
        ))}
      </div>
      <div className="timeline-rail">
        {nodes.map((node) => {
          const firstEvidence = node.evidence_anchors[0];
          const materials = node.materials.map((id) => timeline.materials[id]).filter(Boolean);
          return (
            <article
              className={node.node_id === activeNodeId ? "timeline-node active" : "timeline-node"}
              key={node.node_id}
              data-node-id={node.node_id}
            >
              <button className="node-card" type="button" onClick={() => onSelect(node.node_id)} aria-label={node.headline}>
                <span className="node-meta">
                  <span>{node.date}</span>
                  <span>{node.node_id === activeNodeId ? "当前选中" : node.document_type}</span>
                </span>
                <strong>{node.headline}</strong>
                <span className="node-summary">{node.summary}</span>
                <span className="evidence-preview">
                  <span>证据链</span>
                  <strong>{firstEvidence?.display_value ?? "暂无已抽取关键字段"}</strong>
                  <em>{firstEvidence ? verificationStatusLabel(firstEvidence.verification_status).replace("已核验", "已确认") : "待补充"}</em>
                </span>
                {firstEvidence && (
                  <span className="source-note">
                    <span>材料原文记载</span>
                    <strong>“{firstEvidence.display_value}”</strong>
                  </span>
                )}
                <span className="material-links">
                  <span>原始材料</span>
                  <strong>{materials.map((material) => material.title.replace("合成", "")).join(" · ")}</strong>
                  <span className="material-open" onClick={(event) => {
                    event.stopPropagation();
                    void onOpenEvidence(materials[0]?.material_id ?? node.materials[0], firstEvidence);
                  }}>
                    查看 →
                  </span>
                </span>
                <span className="tag-row" aria-label="节点标签">
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
  onOpenSearchResult,
  relatedResult,
  relatedLoadingKey,
  onRelatedSearch,
  evidenceLoading,
}: {
  timeline: TimelineResponse | null;
  node?: TimelineNode;
  onOpenEvidence: (materialId: string, anchor?: EvidenceAnchor) => Promise<void>;
  onOpenSearchResult: (item: EvidenceSearchItem) => Promise<void>;
  relatedResult: EvidenceSearchResponse | null;
  relatedLoadingKey: string;
  onRelatedSearch: (anchor: EvidenceAnchor) => Promise<void>;
  evidenceLoading: boolean;
}) {
  if (!timeline || !node) {
    return <div className="detail-empty">请选择时间轴节点。</div>;
  }
  const materials = node.materials.map((id) => timeline.materials[id]).filter(Boolean);
  const evidenceByField = new Map(node.evidence_anchors.map((anchor) => [anchor.field_key, anchor]));
  const primaryAnchor = node.evidence_anchors[0];
  return (
    <div className="detail-content">
      <div className="detail-head">
        <span>{node.date}</span>
        <h2>{node.headline}</h2>
        <p>{node.hospital_department}｜{node.document_type}</p>
      </div>

      <section className="event-section">
        <h3>事件说明</h3>
        <p>{node.summary}</p>
      </section>

      <section className="evidence-list" aria-label="证据链">
        <div className="section-title-row">
          <h3>证据链</h3>
          <span>{node.evidence_anchors.length} 项</span>
        </div>
        {node.evidence_anchors.map((anchor) => (
          <div
            className="evidence-item"
            key={anchor.anchor_id}
            role="button"
            tabIndex={0}
            onClick={() => void onOpenEvidence(anchor.material_id, anchor)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") void onOpenEvidence(anchor.material_id, anchor);
            }}
          >
            <FileSearch size={16} />
            <span>{anchor.display_value}</span>
            <small>
              {anchor.bbox ? "原图 bbox 高亮" : "仅材料页定位"}｜{verificationStatusLabel(anchor.verification_status)}｜OCR {Math.round((anchor.ocr_confidence ?? anchor.confidence) * 100)}%
            </small>
            <button
              className="retry-link"
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                void onOpenEvidence(anchor.material_id, anchor);
              }}
            >
              查看原图证据
            </button>
          </div>
        ))}
        {evidenceLoading && <span className="loading-inline">正在打开证据材料...</span>}
      </section>

      {primaryAnchor && (
        <section className="source-record-box">
          <h3>材料原文记载</h3>
          <p>“{primaryAnchor.display_value}”</p>
          <span>来源：{primaryAnchor.field_key}，仅展示原材料中已有文字。</span>
        </section>
      )}

      <section className="field-list" aria-label="结构化字段">
        <div className="section-title-row">
          <h3>结构化字段</h3>
          <span>点击字段核验证据</span>
        </div>
        {Object.entries(node.structured_fields).map(([key, value]) => {
          const anchor = evidenceByField.get(key);
          const confidence = anchor?.ocr_confidence ?? anchor?.confidence;
          return (
            <button
              className={confidence && confidence < 0.85 ? "field-item low" : "field-item"}
              type="button"
              key={key}
              onClick={() => anchor && void onOpenEvidence(anchor.material_id, anchor)}
            >
              <span>{key}</span>
              <strong>{value}</strong>
              {anchor && confidence && (
                <em>
                  {evidenceStatusText(confidence)}｜OCR {Math.round(confidence * 100)}%
                </em>
              )}
              {anchor && (
                <span
                  className="field-related-link"
                  onClick={(event) => {
                    event.stopPropagation();
                    void onRelatedSearch(anchor);
                  }}
                >
                  历史关联记录
                </span>
              )}
            </button>
          );
        })}
      </section>

      <section className="material-stack">
        <div className="section-title-row">
          <h3>原始材料</h3>
          <span>{materials.length} 份</span>
        </div>
        {materials.map((material) => (
          <button
            className="material-link-row"
            type="button"
            key={material.material_id}
            onClick={() => void onOpenEvidence(material.material_id, material.evidence_anchors[0])}
          >
            <FileSearch size={16} />
            <span>{material.title}</span>
            <strong>查看 →</strong>
          </button>
        ))}
      </section>

      <section className="ocr-box">
        <h3>OCR 片段</h3>
        <p>{node.ocr_excerpt}</p>
        {node.evidence_anchors[0] && (
          <button
            className="retry-link related-trigger"
            type="button"
            onClick={() => void onRelatedSearch(node.evidence_anchors[0])}
          >
            联查相关证据
          </button>
        )}
        {relatedLoadingKey && <span className="loading-inline">正在联查相关记录...</span>}
        {relatedResult && (
          <div className="related-records">
            <strong>关联记录（{relatedResult.items.length}）</strong>
            <span>{relatedResult.llm_mode === "mock" ? "本地检索模式" : "provider 回退模式"}</span>
            {relatedResult.items.length === 0 && <p>{relatedResult.not_found_note ?? relatedResult.result_statement}</p>}
            {relatedResult.items.map((item) => (
              <EvidenceResultCard item={item} key={`related-${item.segment_id}`} compact onOpenResult={onOpenSearchResult} />
            ))}
          </div>
        )}
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

function CaptureWorkbench({
  cases,
  selectedCaseId,
  onCaseChange,
  job,
  message,
  onProcess,
}: {
  cases: CaseSummary[];
  selectedCaseId: string;
  onCaseChange: (caseId: string) => void;
  job: IngestionJob | null;
  message: string;
  onProcess: (files: File[], source: "upload" | "camera") => Promise<void>;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [cameraError, setCameraError] = useState("");
  const [stream, setStream] = useState<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
    return () => {
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [stream]);

  async function openCamera() {
    setCameraError("");
    try {
      const media = await navigator.mediaDevices.getUserMedia({ video: true });
      setStream(media);
    } catch {
      setCameraError("摄像头权限不可用，可继续使用文件上传。");
    }
  }

  async function captureFrame() {
    if (!videoRef.current) return;
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth || 900;
    canvas.height = videoRef.current.videoHeight || 620;
    canvas.getContext("2d")?.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"));
    if (blob) {
      await onProcess([new File([blob], "camera-capture.png", { type: "image/png" })], "camera");
    }
  }

  return (
    <main className="single-pane">
      <section className="capture-grid">
        <div className="capture-panel">
          <div className="panel-heading">
            <span>采集新材料</span>
            <h2>现场合成材料处理</h2>
            <p>{SAFETY_NOTICE}</p>
          </div>
          <label className="control-label" htmlFor="capture-case">
            接入病例
          </label>
          <select id="capture-case" value={selectedCaseId} onChange={(event) => onCaseChange(event.target.value)}>
            {cases.map((item) => (
              <option key={item.case_id} value={item.case_id}>
                {item.patient_display}｜{item.destination_department}
              </option>
            ))}
          </select>

          <label className="dropzone">
            <Upload size={22} />
            <strong>上传 PNG/JPG 合成材料</strong>
            <span>单次最多 10 张，每张最大 10 MB</span>
            <input
              aria-label="上传合成材料图片"
              type="file"
              accept=".png,.jpg,.jpeg"
              multiple
              onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
            />
          </label>
          {files.length > 0 && (
            <div className="selected-files">
              {files.map((file) => (
                <span key={`${file.name}-${file.size}`}>{file.name}</span>
              ))}
            </div>
          )}
          <button className="icon-button primary" type="button" disabled={!files.length} onClick={() => void onProcess(files, "upload")}>
            <Upload size={17} />
            开始处理
          </button>
        </div>

        <div className="capture-panel">
          <div className="panel-heading">
            <span>摄像头</span>
            <h2>单帧采集合成材料</h2>
            <p>请只拍摄提供的合成演示材料。</p>
          </div>
          <div className="camera-box">
            {stream ? <video ref={videoRef} autoPlay playsInline muted /> : <Camera size={38} />}
          </div>
          <div className="camera-actions">
            <button className="icon-button" type="button" onClick={() => void openCamera()}>
              <Camera size={17} />
              开启摄像头
            </button>
            <button className="icon-button primary" type="button" disabled={!stream} onClick={() => void captureFrame()}>
              拍摄本页
            </button>
          </div>
          {cameraError && <div className="inline-warning">{cameraError}</div>}
        </div>
      </section>

      <ProcessingStatus job={job} message={message} />
    </main>
  );
}

function ProcessingStatus({ job, message }: { job: IngestionJob | null; message: string }) {
  return (
    <section className="processing-panel" aria-label="处理状态">
      <div className="panel-heading">
        <span>处理状态</span>
        <h2>{message || "等待合成材料"}</h2>
      </div>
      {job && (
        <>
          <div className="stepper">
            {job.steps.map((step) => (
              <div className={`step ${step.status}`} key={step.name}>
                <strong>{step.name}</strong>
                <span>{step.status === "completed" && step.mode ? "预置合成 OCR 演示回放" : step.status}</span>
              </div>
            ))}
          </div>
          <div className="quality-grid">
            {job.materials.map((material, index) => (
              <div className={`quality-card ${material.quality.status}`} key={`${material.source_file}-${index}`}>
                <strong>{material.source_file ?? material.title}</strong>
                <span>{qualityStatusLabel(material.quality.status)}</span>
                <small>
                  blur {material.quality.blur_score}｜glare {material.quality.glare_ratio}
                </small>
                {material.quality.messages.map((item) => (
                  <p key={item}>{item}</p>
                ))}
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function PreConsultSummary({ summary, onRefresh }: { summary: CaseSummaryV2 | null; onRefresh: () => void }) {
  if (!summary) {
    return (
      <main className="single-pane">
        <div className="empty-state">
          <ClipboardList size={28} />
          <strong>暂无摘要数据</strong>
          <button className="icon-button primary" type="button" onClick={onRefresh}>
            <RefreshCw size={17} />
            重新生成
          </button>
        </div>
      </main>
    );
  }
  return (
    <main className="single-pane">
      <section className="summary-page">
        <div className="panel-heading">
          <span>接诊前摘要</span>
          <h2>历刻｜合成演示接诊前整理摘要</h2>
          <p>{summary.boundary}</p>
        </div>
        <div className="summary-grid">
          <div><span>患者</span><strong>{summary.patient_display}</strong></div>
          <div><span>转院路径</span><strong>{summary.transfer_path}</strong></div>
          <div><span>覆盖时间</span><strong>{summary.coverage}</strong></div>
          <div><span>节点/现场材料</span><strong>{summary.node_count} 个节点｜{summary.uploaded_material_count} 份</strong></div>
          <div><span>已确认字段</span><strong>{summary.review_counts.confirmed}</strong></div>
          <div><span>待核验/需复核字段</span><strong>{summary.review_counts.needs_review}</strong></div>
        </div>
        <section className="summary-section">
          <h3>与转院原因相关的节点</h3>
          {summary.transfer_related_nodes.map((node) => (
            <p key={`${node.date}-${node.headline}`}>{node.date}｜{node.document_type}｜{node.headline}</p>
          ))}
        </section>
        <section className="missing-box">
          <h3>材料完整性提示</h3>
          {summary.missing_material_reminders.map((item) => (
            <p key={item}>{item}</p>
          ))}
        </section>
      </section>
    </main>
  );
}

function EvidenceModal({
  selection,
  onClose,
  onReview,
}: {
  selection: EvidenceSelection;
  onClose: () => void;
  onReview: (anchor: EvidenceAnchor, action: ReviewAction, correctedValue?: string, note?: string) => void;
}) {
  const anchor = selection.anchor;
  const [correctedValue, setCorrectedValue] = useState(anchor?.display_value ?? "");
  const confidence = anchor ? anchor.ocr_confidence ?? anchor.confidence : undefined;
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
          <EvidenceCanvas material={selection.material} anchor={anchor} />
          <div className="source-detail">
            {anchor && confidence ? (
              <>
                <div className={confidence < 0.85 ? "confidence low" : "confidence"}>
                  <CheckCircle2 size={16} />
                  <span>OCR 置信度 {Math.round(confidence * 100)}%｜{evidenceStatusText(confidence)}</span>
                </div>
                <dl>
                  <dt>字段</dt>
                  <dd>{anchor.field_key}</dd>
                  <dt>提取值</dt>
                  <dd>{anchor.display_value}</dd>
                  <dt>位置</dt>
                  <dd>{anchor.bbox ? "原图 bbox 高亮" : anchor.page_or_image}</dd>
                  <dt>核验状态</dt>
                  <dd>{verificationStatusLabel(anchor.verification_status)}</dd>
                  <dt>OCR 模式</dt>
                  <dd>{selection.material.ocr_mode_label ?? "旧版定位说明"}</dd>
                </dl>
                <div className="review-actions" aria-label="医生核验操作">
                  <button type="button" className="icon-button primary" onClick={() => onReview(anchor, "confirmed", undefined, "确认正确")}>
                    确认正确
                  </button>
                  <button type="button" className="icon-button" onClick={() => onReview(anchor, "needs_review", undefined, "标记需复核")}>
                    标记需复核
                  </button>
                  <label>
                    修改字段
                    <input value={correctedValue} onChange={(event) => setCorrectedValue(event.target.value)} />
                  </label>
                  <button type="button" className="icon-button" onClick={() => onReview(anchor, "corrected", correctedValue, "演示修改字段")}>
                    保存修改
                  </button>
                </div>
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

function EvidenceCanvas({ material, anchor }: { material: Material; anchor?: EvidenceAnchor }) {
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [box, setBox] = useState<CSSProperties | null>(null);

  function updateBox() {
    const image = imageRef.current;
    if (!image || !anchor?.bbox || !image.naturalWidth || !image.naturalHeight) {
      setBox(null);
      return;
    }
    const [x1, y1, x2, y2] = anchor.bbox;
    setBox({
      left: `${(x1 / image.naturalWidth) * 100}%`,
      top: `${(y1 / image.naturalHeight) * 100}%`,
      width: `${((x2 - x1) / image.naturalWidth) * 100}%`,
      height: `${((y2 - y1) / image.naturalHeight) * 100}%`,
    });
  }

  return (
    <div className="source-image-wrap">
      <img ref={imageRef} src={assetUrl(material.image_url)} alt={`${material.title}合成原始材料`} onLoad={updateBox} />
      {box ? (
        <div className="bbox-highlight" style={box}>
          {anchor?.field_key}
        </div>
      ) : (
        anchor && <div className="locator-highlight">定位：{anchor.locator_text}</div>
      )}
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
