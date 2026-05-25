import type { CaseListResponse, Material, TimelineResponse, UploadResponse } from "./types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

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

export function assetUrl(imageUrl: string): string {
  return `${API_BASE_URL}${imageUrl}`;
}
