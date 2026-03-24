"use client";

import { useEffect, useState } from "react";
import { Shield, MessageSquare } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SeverityBadge } from "@/components/severity-badge";
import { FindingCard } from "@/components/finding-card";
import { SeverityChart } from "@/components/severity-chart";
import { getFindings } from "@/lib/api";
import type { Finding, FindingsResponse } from "@/lib/types";
import { SEVERITY_ORDER } from "@/lib/types";

interface FindingsDashboardProps {
  scanId: string;
  targetUrl: string;
}

export function FindingsDashboard({ scanId, targetUrl }: FindingsDashboardProps) {
  const [data, setData] = useState<FindingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string | null>(null);

  useEffect(() => {
    getFindings(scanId, filter ? { severity: filter } : undefined)
      .then(setData)
      .finally(() => setLoading(false));
  }, [scanId, filter]);

  if (loading) {
    return (
      <Card className="animate-pulse space-y-4">
        <div className="h-6 bg-[var(--card-border)] rounded w-1/3" />
        <div className="h-40 bg-[var(--card-border)] rounded" />
      </Card>
    );
  }

  if (!data) return null;

  const grouped = SEVERITY_ORDER.reduce((acc, sev) => {
    const items = data.findings.filter((f) => f.severity === sev);
    if (items.length > 0) acc.push({ severity: sev, findings: items });
    return acc;
  }, [] as { severity: string; findings: Finding[] }[]);

  const totalFindings = Object.values(data.summary).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6">
      {/* Summary Header */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-[var(--accent)]" />
              <h2 className="text-lg font-bold">Scan Results</h2>
            </div>
            <p className="text-sm text-[var(--muted)] mt-1">{targetUrl}</p>
          </div>
          <a href={`/scans/${scanId}/chat`}>
            <Button size="sm">
              <MessageSquare className="h-4 w-4 mr-2" />
              Ask wvs
            </Button>
          </a>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFilter(null)}
            className={`text-xs px-3 py-1 rounded-full border transition-colors ${
              !filter
                ? "bg-[var(--accent)] text-[var(--accent-foreground)] border-[var(--accent)]"
                : "border-[var(--card-border)] hover:bg-[var(--card-border)]"
            }`}
          >
            All ({totalFindings})
          </button>
          {SEVERITY_ORDER.map((sev) => {
            const count = data.summary[sev] || 0;
            if (count === 0) return null;
            return (
              <button
                key={sev}
                onClick={() => setFilter(filter === sev ? null : sev)}
                className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                  filter === sev
                    ? "bg-[var(--accent)] text-[var(--accent-foreground)] border-[var(--accent)]"
                    : "border-[var(--card-border)] hover:bg-[var(--card-border)]"
                }`}
              >
                {sev} ({count})
              </button>
            );
          })}
        </div>
      </Card>

      {/* Chart */}
      {totalFindings > 0 && <SeverityChart summary={data.summary} />}

      {/* Findings grouped by severity */}
      {grouped.length === 0 ? (
        <Card className="text-center py-12">
          <Shield className="h-12 w-12 mx-auto text-[var(--accent)] mb-3" />
          <h3 className="font-semibold">No Vulnerabilities Found</h3>
          <p className="text-sm text-[var(--muted)] mt-1">
            {filter ? `No ${filter} findings.` : "Great news! The scan did not detect any vulnerabilities."}
          </p>
        </Card>
      ) : (
        grouped.map(({ severity, findings }) => (
          <div key={severity} className="space-y-2">
            <div className="flex items-center gap-2">
              <SeverityBadge severity={severity} />
              <span className="text-sm text-[var(--muted)]">
                {findings.length} finding{findings.length !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="space-y-2">
              {findings.map((f) => (
                <FindingCard key={f.id} finding={f} />
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
