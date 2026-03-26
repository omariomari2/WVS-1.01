export type FindingSeverity =
  | "Critical"
  | "High"
  | "Medium"
  | "Low"
  | "Informational";

export type FindingFilter =
  | "all"
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "informational";

export interface Finding {
  id: string;
  scan_id: string;
  owasp_category: string;
  owasp_name: string;
  severity: FindingSeverity;
  title: string;
  description: string;
  evidence: string | null;
  url: string;
  remediation: string;
  confidence: "High" | "Medium" | "Low";
  created_at: string;
}

export interface FindingsResponse {
  findings: Finding[];
  summary: Record<string, number>;
}

export const FINDING_FILTER_OPTIONS = [
  { id: "all", label: "All" },
  { id: "critical", label: "Critical" },
  { id: "high", label: "High" },
  { id: "medium", label: "Medium" },
  { id: "low", label: "Low" },
  { id: "informational", label: "Informational" },
] as const satisfies ReadonlyArray<{ id: FindingFilter; label: string }>;
