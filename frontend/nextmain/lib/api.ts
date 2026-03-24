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
