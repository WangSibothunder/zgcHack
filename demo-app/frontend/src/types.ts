export type TagLevel = "info" | "warning" | "danger" | "success";
export type VerificationStatus = "unreviewed" | "confirmed" | "needs_review";
export type ReviewAction = "confirmed" | "needs_review" | "corrected";

export interface CaseSummary {
  case_id: string;
  patient_display: string;
  destination_department: string;
  transfer_reason: string;
  node_count: number;
  abnormal_flag_count: number;
}

export interface CaseListResponse {
  synthetic: true;
  notice: string;
  cases: CaseSummary[];
}

export interface Patient {
  display_name: string;
  sex: string;
  age_display: string;
}

export interface TransferContext {
  origin_hospital: string;
  destination_hospital: string;
  destination_department: string;
  reason: string;
  coverage: string;
}

export interface TimelineTag {
  label: string;
  level: TagLevel;
}

export interface EvidenceAnchor {
  anchor_id: string;
  material_id: string;
  field_key: string;
  display_value: string;
  page_or_image: string;
  locator_text: string;
  confidence: number;
  ocr_confidence?: number;
  extraction_confidence?: number;
  verification_status: VerificationStatus;
  is_abnormal_flag: boolean;
  ocr_block_ids?: string[];
  bbox?: [number, number, number, number];
  source_mode?: string;
  corrected_value?: string;
  correction_note?: string;
}

export interface OCRBlock {
  block_id: string;
  text: string;
  bbox: [number, number, number, number];
  confidence: number;
}

export interface QualityResult {
  status: "pass" | "warning" | "retake_required";
  blur_score: number;
  glare_ratio: number;
  messages: string[];
}

export interface Material {
  synthetic?: true;
  notice?: string;
  material_id: string;
  title: string;
  image_url: string;
  ocr_text: string;
  ocr_mode?: string;
  ocr_mode_label?: string;
  ocr_blocks?: OCRBlock[];
  quality?: QualityResult;
  processing_source?: string;
  evidence_anchors: EvidenceAnchor[];
}

export interface TimelineNode {
  node_id: string;
  date: string;
  hospital_department: string;
  document_type: string;
  headline: string;
  summary: string;
  tags: TimelineTag[];
  related_to_transfer_reason: boolean;
  has_abnormal_flag: boolean;
  materials: string[];
  structured_fields: Record<string, string>;
  ocr_excerpt: string;
  processing_source?: string;
  evidence_anchors: EvidenceAnchor[];
}

export interface AvailableFilters {
  abnormal_only: boolean;
  document_types: string[];
  transfer_related: boolean;
}

export interface TimelineResponse {
  synthetic: true;
  notice: string;
  case_id: string;
  patient: Patient;
  transfer: TransferContext;
  timeline_nodes: TimelineNode[];
  materials: Record<string, Material>;
  available_filters: AvailableFilters;
  missing_material_reminders: string[];
}

export interface UploadResponse {
  job_id: string;
  status: "completed";
  synthetic: true;
  generated_case_id: string;
  file_count?: number;
  message: string;
}

export interface ProcessingStep {
  name: string;
  status: string;
  mode?: string;
}

export interface IngestionMaterialResult {
  source_file?: string;
  material_id?: string;
  title?: string;
  image_url?: string;
  quality: QualityResult;
  status?: string;
  ocr_mode?: string;
  ocr_mode_label?: string;
}

export interface IngestionJob {
  job_id: string;
  synthetic: true;
  status: "uploaded" | "quality_checking" | "retake_required" | "ocr_processing" | "extracting_fields" | "timeline_generated" | "failed";
  processing_mode: "live_synthetic_upload";
  created_at: string;
  generated_case_id: string;
  generated_node_ids: string[];
  materials: IngestionMaterialResult[];
  steps: ProcessingStep[];
  message: string;
}

export interface EvidenceReview {
  review_id: string;
  anchor_id: string;
  action: ReviewAction;
  before_value: string;
  after_value: string;
  note: string;
  reviewer_role: string;
  reviewed_at: string;
  synthetic: true;
}

export interface CaseSummaryV2 {
  synthetic: true;
  notice: string;
  case_id: string;
  patient_display: string;
  transfer_path: string;
  coverage: string;
  node_count: number;
  uploaded_material_count: number;
  transfer_related_nodes: Array<{ date: string; headline: string; document_type: string }>;
  review_counts: {
    confirmed: number;
    needs_review: number;
    corrected: number;
    unreviewed: number;
  };
  missing_material_reminders: string[];
  boundary: string;
}

export type EvidenceSearchTrigger = "question" | "selection" | "field";

export interface EvidenceSearchItem {
  rank: number;
  relevance_level: "direct_mention" | "synonymous_mention" | "contextual";
  relevance_label: string;
  material_id: string;
  node_id: string;
  segment_id: string;
  anchor_id?: string;
  document_date: string | null;
  document_type: string;
  hospital_name?: string | null;
  department?: string | null;
  source_excerpt: string;
  evidence_summary: string;
  bbox?: [number, number, number, number] | null;
  ocr_confidence: number;
  ranking_source: string;
  verification_status: VerificationStatus;
}

export interface EvidenceSearchRequest {
  case_id: string;
  trigger_type: EvidenceSearchTrigger;
  question?: string;
  selected_segment_ids?: string[];
  selected_material_id?: string;
  selected_text?: string;
  top_k?: number;
}

export interface EvidenceSearchResponse {
  query_id: string;
  case_id: string;
  answer_mode: "evidence_only";
  query_display: string;
  retrieval_terms: string[];
  result_statement: string;
  items: EvidenceSearchItem[];
  not_found_note: string | null;
  llm_mode: "external_api" | "mock" | "unavailable_fallback" | string;
  notice: string;
  synthetic: true;
}
