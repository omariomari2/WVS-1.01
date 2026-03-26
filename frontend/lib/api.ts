import type { FindingsResponse, PrCommit, RectifyResponse, ScanResponse } from "@/lib/types";

function getApiBase(): string {
  if (typeof window === "undefined") return "";
  const origin = window.location.origin;
  const port = window.location.port;
  if (origin.includes("localhost") && !port.includes("4500")) {
    return "http://localhost:4500";
  }
  return "";
}

async function postJSON(endpoint: string, body: Record<string, unknown>) {
  const response = await fetch(`${getApiBase()}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return response;
}

export async function formatHTML(html: string): Promise<{ success: boolean; data?: string; error?: string }> {
  const response = await postJSON("/api/format", { html });
  return response.json();
}

export async function exportZip(html: string): Promise<{ blob: Blob; filename: string }> {
  const response = await postJSON("/api/export", { html });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Export failed");
  }
  const blob = await response.blob();
  return { blob, filename: "extracted.zip" };
}

export async function exportTSXProject(html: string): Promise<{ blob: Blob; filename: string }> {
  const response = await postJSON("/api/export-nodejs", { html });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Export failed");
  }
  const blob = await response.blob();
  const cd = response.headers.get("Content-Disposition");
  const filename = cd
    ? cd.split("filename=")[1]?.replace(/"/g, "") || "project.zip"
    : "project.zip";
  return { blob, filename };
}

export async function exportEJSProject(html: string): Promise<{ blob: Blob; filename: string }> {
  const response = await postJSON("/api/export-nodejs-ejs", { html });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Export failed");
  }
  const blob = await response.blob();
  const cd = response.headers.get("Content-Disposition");
  const filename = cd
    ? cd.split("filename=")[1]?.replace(/"/g, "") || "project-ejs.zip"
    : "project-ejs.zip";
  return { blob, filename };
}

export async function scrapeAndExport(
  url: string,
  exportType: "zip" | "nodejs" | "ejs"
): Promise<{ blob: Blob; filename: string }> {
  const endpointMap: Record<string, string> = {
    zip: "/api/scrape",
    nodejs: "/api/scrape-nodejs",
    ejs: "/api/scrape-nodejs-ejs",
  };

  const response = await postJSON(endpointMap[exportType], { url });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Scrape failed");
  }

  const blob = await response.blob();
  const cd = response.headers.get("Content-Disposition");
  const defaultName =
    exportType === "ejs"
      ? "project-ejs.zip"
      : exportType === "nodejs"
        ? "project.zip"
        : "extracted.zip";
  const filename = cd
    ? cd.split("filename=")[1]?.replace(/"/g, "") || defaultName
    : defaultName;

  return { blob, filename };
}

const BACKEND_URL = "http://localhost:8000/api";

export async function createScan(url: string, speed: "fast" | "thorough" = "fast") {
  const res = await fetch(`${BACKEND_URL}/scans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_url: url, scan_speed: speed, authorization_confirmed: true }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create scan");
  }
  return res.json();
}

export async function getFindings(scanId: string): Promise<FindingsResponse> {
  const res = await fetch(`${BACKEND_URL}/scans/${scanId}/findings`);
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch findings");
  }
  return res.json();
}

export async function getScan(scanId: string) {
  const res = await fetch(`${BACKEND_URL}/scans/${scanId}`);
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch scan");
  }
  return res.json();
}

export async function exportFindings(
  scanId: string,
  format: "json" | "csv" | "pdf" | "md"
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(
    `${BACKEND_URL}/scans/${scanId}/findings/export/file?format=${format}`
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Export failed" }));
    throw new Error(err.detail || "Export failed");
  }
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition");
  const defaultName = `wvs_report.${format}`;
  const filename = cd
    ? cd.split("filename=")[1]?.replace(/"/g, "") || defaultName
    : defaultName;
  return { blob, filename };
}

export async function createPrScan(prUrl: string): Promise<ScanResponse> {
  const res = await fetch(`${BACKEND_URL}/pr-scans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pr_url: prUrl }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create PR scan");
  }
  return res.json();
}

export async function getPrScan(scanId: string): Promise<ScanResponse> {
  const res = await fetch(`${BACKEND_URL}/pr-scans/${scanId}`);
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch PR scan");
  }
  return res.json();
}

export async function getPrCommits(scanId: string): Promise<PrCommit[]> {
  const res = await fetch(`${BACKEND_URL}/pr-scans/${scanId}/commits`);
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to fetch commits");
  }
  return res.json();
}

export async function rectifySend(scanId: string, findingId: string): Promise<RectifyResponse> {
  const res = await fetch(`${BACKEND_URL}/pr-scans/${scanId}/rectify/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ finding_id: findingId }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Rectify send failed");
  }
  return res.json();
}

export async function rectifyApply(scanId: string, findingId: string): Promise<RectifyResponse> {
  const res = await fetch(`${BACKEND_URL}/pr-scans/${scanId}/rectify/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ finding_id: findingId }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Rectify apply failed");
  }
  return res.json();
}

export async function rectifyComment(scanId: string, findingId: string): Promise<RectifyResponse> {
  const res = await fetch(`${BACKEND_URL}/pr-scans/${scanId}/rectify/comment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ finding_id: findingId }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Rectify comment failed");
  }
  return res.json();
}

export async function rectifyReview(scanId: string): Promise<RectifyResponse> {
  const res = await fetch(`${BACKEND_URL}/pr-scans/${scanId}/rectify/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Rectify review failed");
  }
  return res.json();
}

export async function rectifyBatch(
  scanId: string,
  findingIds: string[],
  action: "send" | "apply" | "comment"
): Promise<RectifyResponse[]> {
  const res = await fetch(`${BACKEND_URL}/pr-scans/${scanId}/rectify/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ finding_ids: findingIds, action }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Rectify batch failed");
  }
  return res.json();
}
