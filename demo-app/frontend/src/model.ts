import type { TimelineNode } from "./types";

export type NodeFilter =
  | { kind: "all" }
  | { kind: "abnormal" }
  | { kind: "transfer" }
  | { kind: "document_type"; value: string }
  | { kind: "empty_demo" };

export function filterNodes(nodes: TimelineNode[], filter: NodeFilter): TimelineNode[] {
  const sorted = [...nodes].sort((a, b) => a.date.localeCompare(b.date));
  if (filter.kind === "all") return sorted;
  if (filter.kind === "abnormal") return sorted.filter((node) => node.has_abnormal_flag);
  if (filter.kind === "transfer") return sorted.filter((node) => node.related_to_transfer_reason);
  if (filter.kind === "empty_demo") return [];
  return sorted.filter((node) => node.document_type.includes(filter.value));
}

export function evidenceStatusText(confidence: number): string {
  if (confidence < 0.85) return "低置信度，待核验";
  return "待医生核验";
}

export function verificationStatusLabel(status: string): string {
  if (status === "confirmed") return "已核验";
  if (status === "needs_review") return "需复核";
  return "未核验";
}
