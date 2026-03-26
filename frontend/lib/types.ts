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
  file_path: string | null;
  line_number: number | null;
  commit_sha: string | null;
  code_snippet: string | null;
  diff_hunk: string | null;
  rule_id: string | null;
  cwe: string | null;
}

export interface FindingsResponse {
  findings: Finding[];
  summary: Record<string, number>;
}

export interface PrCommit {
  id: string;
  scan_id: string;
  sha: string;
  message: string;
  author: string;
  created_at: string;
}

export interface ScanResponse {
  id: string;
  target_url: string;
  status: string;
  progress: number;
  current_module: string | null;
  total_findings: number;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  scan_type: string;
  pr_url: string | null;
  pr_number: number | null;
  repo_owner: string | null;
  repo_name: string | null;
  pr_title: string | null;
  pr_branch: string | null;
  base_branch: string | null;
  head_sha: string | null;
  local_repo_path: string | null;
}

export interface RectifyResponse {
  success: boolean;
  action: string;
  finding_id: string;
  content: string | null;
  diff_preview: string | null;
  message: string | null;
}

export type RectifyAction = "send" | "apply" | "comment" | "review";

export const FINDING_FILTER_OPTIONS = [
  { id: "all", label: "All" },
  { id: "critical", label: "Critical" },
  { id: "high", label: "High" },
  { id: "medium", label: "Medium" },
  { id: "low", label: "Low" },
  { id: "informational", label: "Informational" },
] as const satisfies ReadonlyArray<{ id: FindingFilter; label: string }>;
