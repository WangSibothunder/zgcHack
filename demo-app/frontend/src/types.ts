export type TagLevel = "info" | "warning" | "danger" | "success";
export type VerificationStatus = "unreviewed" | "confirmed" | "needs_review";

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
  verification_status: VerificationStatus;
  is_abnormal_flag: boolean;
}

export interface Material {
  synthetic?: true;
  notice?: string;
  material_id: string;
  title: string;
  image_url: string;
  ocr_text: string;
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
