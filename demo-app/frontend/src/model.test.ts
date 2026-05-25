import { describe, expect, it } from "vitest";
import { evidenceStatusText, filterNodes, type NodeFilter } from "./model";
import type { TimelineNode } from "./types";

const baseNode = (overrides: Partial<TimelineNode>): TimelineNode => ({
  node_id: "node-a",
  date: "2025-01-01",
  hospital_department: "合成医院｜科室",
  document_type: "门诊记录",
  headline: "合成节点",
  summary: "合成概要",
  tags: [],
  related_to_transfer_reason: false,
  has_abnormal_flag: false,
  materials: ["mat-a"],
  structured_fields: {},
  ocr_excerpt: "合成 OCR",
  evidence_anchors: [],
  ...overrides,
});

describe("timeline filtering", () => {
  const nodes = [
    baseNode({ node_id: "late", date: "2025-01-03", document_type: "出院小结" }),
    baseNode({
      node_id: "early",
      date: "2025-01-01",
      document_type: "影像报告",
      has_abnormal_flag: true,
      related_to_transfer_reason: true,
    }),
    baseNode({ node_id: "middle", date: "2025-01-02", document_type: "门诊记录" }),
  ];

  it("keeps filtered results chronologically sorted", () => {
    const result = filterNodes(nodes, { kind: "all" });
    expect(result.map((node) => node.node_id)).toEqual(["early", "middle", "late"]);
  });

  it("filters abnormal and transfer-related nodes", () => {
    expect(filterNodes(nodes, { kind: "abnormal" }).map((node) => node.node_id)).toEqual(["early"]);
    expect(filterNodes(nodes, { kind: "transfer" }).map((node) => node.node_id)).toEqual(["early"]);
  });

  it("filters by document type and exposes empty state", () => {
    const documentFilter: NodeFilter = { kind: "document_type", value: "出院小结" };
    expect(filterNodes(nodes, documentFilter).map((node) => node.node_id)).toEqual(["late"]);
    expect(filterNodes(nodes, { kind: "empty_demo" })).toEqual([]);
  });
});

describe("evidence confidence labels", () => {
  it("marks low confidence evidence for review", () => {
    expect(evidenceStatusText(0.82)).toBe("低置信度，待核验");
    expect(evidenceStatusText(0.91)).toBe("待医生核验");
  });
});
