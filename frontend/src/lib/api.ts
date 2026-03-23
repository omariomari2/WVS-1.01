import type { Scan, FindingsResponse, ChatMessage } from "./types";

const API_BASE = "/api";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function createScan(targetUrl: string): Promise<Scan> {
  return fetchJson<Scan>("/scans", {
    method: "POST",
    body: JSON.stringify({
      target_url: targetUrl,
      authorization_confirmed: true,
    }),
  });
}

export async function listScans(): Promise<Scan[]> {
  return fetchJson<Scan[]>("/scans");
}

export async function getScan(scanId: string): Promise<Scan> {
  return fetchJson<Scan>(`/scans/${scanId}`);
}

export async function deleteScan(scanId: string): Promise<void> {
  await fetch(`${API_BASE}/scans/${scanId}`, { method: "DELETE" });
}

export async function getFindings(
  scanId: string,
  filters?: { severity?: string; category?: string }
): Promise<FindingsResponse> {
  const params = new URLSearchParams();
  if (filters?.severity) params.set("severity", filters.severity);
  if (filters?.category) params.set("category", filters.category);
  const qs = params.toString();
  return fetchJson<FindingsResponse>(
    `/scans/${scanId}/findings${qs ? `?${qs}` : ""}`
  );
}

export async function getChatHistory(scanId: string): Promise<ChatMessage[]> {
  return fetchJson<ChatMessage[]>(`/scans/${scanId}/chat/history`);
}

export async function* streamChat(
  scanId: string,
  message: string
): AsyncGenerator<string> {
  const res = await fetch(`${API_BASE}/scans/${scanId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") return;
        yield data;
      }
    }
  }
}
