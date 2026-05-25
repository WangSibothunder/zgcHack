import type {
  CaseListResponse,
  CaseSummaryV2,
  EvidenceReview,
  EvidenceSearchRequest,
  EvidenceSearchResponse,
  IngestionJob,
  Material,
  ReviewAction,
  TimelineResponse,
  UploadResponse,
} from "./types";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.PROD ? "" : "http://127.0.0.1:8000");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getCases(): Promise<CaseListResponse> {
  return request<CaseListResponse>("/api/v1/demo/cases");
}

export function getTimeline(caseId: string): Promise<TimelineResponse> {
  return request<TimelineResponse>(`/api/v1/demo/cases/${caseId}/timeline`);
}

export function getMaterial(caseId: string, materialId: string): Promise<Material> {
  return request<Material>(`/api/v1/demo/cases/${caseId}/materials/${materialId}`);
}

export function createUploadJob(fixtureCaseId: string, fileNames: string[]): Promise<UploadResponse> {
  return request<UploadResponse>("/api/v1/demo/uploads", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      fixture_case_id: fixtureCaseId,
      file_names: fileNames,
    }),
  });
}

export function getJob(jobId: string): Promise<UploadResponse> {
  return request<UploadResponse>(`/api/v1/demo/jobs/${jobId}`);
}

export function createIngestionJob(files: File[], caseId: string, source: "upload" | "camera"): Promise<IngestionJob> {
  const body = new FormData();
  for (const file of files) {
    body.append("files", file);
  }
  body.append("case_id", caseId);
  body.append("source", source);
  body.append("synthetic_acknowledged", "true");
  return request<IngestionJob>("/api/v2/demo/ingestions", {
    method: "POST",
    body,
  });
}

export function getIngestionJob(jobId: string): Promise<IngestionJob> {
  return request<IngestionJob>(`/api/v2/demo/jobs/${jobId}`);
}

export function reviewEvidence(
  anchorId: string,
  payload: { action: ReviewAction; corrected_value?: string; note?: string },
): Promise<EvidenceReview> {
  return request<EvidenceReview>(`/api/v2/demo/evidence/${anchorId}/reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      reviewer_role: "接诊医生（演示）",
      ...payload,
    }),
  });
}

export function getPreConsultSummary(caseId: string): Promise<CaseSummaryV2> {
  return request<CaseSummaryV2>(`/api/v2/demo/cases/${caseId}/summary`);
}

export function rebuildEvidenceSegments(caseId: string): Promise<{ case_id: string; segment_count: number; index_mode: string; synthetic: true }> {
  return request(`/api/v3/demo/cases/${caseId}/segments/rebuild`, {
    method: "POST",
  });
}

export function searchEvidence(payload: EvidenceSearchRequest): Promise<EvidenceSearchResponse> {
  return request<EvidenceSearchResponse>("/api/v3/demo/evidence-search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function assetUrl(imageUrl: string): string {
  return `${API_BASE_URL}${imageUrl}`;
}
