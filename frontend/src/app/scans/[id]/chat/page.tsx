"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Card } from "@/components/ui/card";
import { ChatPanel } from "@/components/chat-panel";
import { SeverityBadge } from "@/components/severity-badge";
import { getScan, getFindings } from "@/lib/api";
import type { Scan, Finding } from "@/lib/types";
import { SEVERITY_ORDER } from "@/lib/types";

export default function ChatPage() {
  const params = useParams<{ id: string }>();
  const [scan, setScan] = useState<Scan | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    getScan(params.id).then(setScan);
    getFindings(params.id).then((data) => setFindings(data.findings));
  }, [params.id]);

  const groupedFindings = SEVERITY_ORDER.reduce((acc, sev) => {
    const items = findings.filter((f) => f.severity === sev);
    if (items.length > 0) acc.push({ severity: sev, findings: items });
    return acc;
  }, [] as { severity: string; findings: Finding[] }[]);

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Findings Sidebar */}
      {sidebarOpen && (
        <div className="w-80 border-r border-[var(--card-border)] overflow-y-auto p-4 space-y-4 hidden lg:block">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Findings</h3>
            <span className="text-xs text-[var(--muted)]">{findings.length} total</span>
          </div>

          {groupedFindings.map(({ severity, findings: items }) => (
            <div key={severity} className="space-y-1">
              <div className="flex items-center gap-2 mb-1">
                <SeverityBadge severity={severity} className="text-[9px] px-1.5 py-0" />
                <span className="text-xs text-[var(--muted)]">({items.length})</span>
              </div>
              {items.map((f) => (
                <div
                  key={f.id}
                  className="text-xs p-2 rounded border border-[var(--card-border)] hover:bg-[var(--card-border)]/30 cursor-default"
                >
                  <p className="font-medium truncate">{f.title}</p>
                  <p className="text-[var(--muted)] truncate">{f.owasp_category}: {f.owasp_name}</p>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="border-b border-[var(--card-border)] px-4 py-2 flex items-center gap-3">
          <a
            href={`/scans/${params.id}`}
            className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] inline-flex items-center gap-1"
          >
            <ArrowLeft className="h-4 w-4" />
            Results
          </a>
          {scan && (
            <span className="text-xs text-[var(--muted)] truncate">
              {scan.target_url}
            </span>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="ml-auto text-xs text-[var(--muted)] hover:text-[var(--foreground)] hidden lg:block"
          >
            {sidebarOpen ? "Hide" : "Show"} findings
          </button>
        </div>

        <ChatPanel scanId={params.id} />
      </div>
    </div>
  );
}
