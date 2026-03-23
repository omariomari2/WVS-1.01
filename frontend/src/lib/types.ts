export interface Scan {
  id: string;
  target_url: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  current_module: string | null;
  total_findings: number;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface Finding {
  id: string;
  scan_id: string;
  owasp_category: string;
  owasp_name: string;
  severity: "Critical" | "High" | "Medium" | "Low" | "Informational";
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

export interface ChatMessage {
  id: string;
  scan_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ScanProgress {
  type: "progress" | "completed" | "error";
  progress: number;
  current_module?: string;
  findings_so_far?: number;
  total_findings?: number;
  message?: string;
}

export const SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Informational"] as const;

export const SEVERITY_COLORS: Record<string, string> = {
  Critical: "bg-red-900 text-red-100",
  High: "bg-red-500 text-white",
  Medium: "bg-orange-500 text-white",
  Low: "bg-yellow-500 text-black",
  Informational: "bg-blue-500 text-white",
};

export const SEVERITY_CHART_COLORS: Record<string, string> = {
  Critical: "#7f1d1d",
  High: "#ef4444",
  Medium: "#f97316",
  Low: "#eab308",
  Informational: "#3b82f6",
};
