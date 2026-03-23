"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { SeverityBadge } from "@/components/severity-badge";
import type { Finding } from "@/lib/types";

interface FindingCardProps {
  finding: Finding;
}

export function FindingCard({ finding }: FindingCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-[var(--card-border)] rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 p-4 text-left hover:bg-[var(--card-border)]/30 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 mt-0.5 shrink-0 text-[var(--muted)]" />
        ) : (
          <ChevronRight className="h-4 w-4 mt-0.5 shrink-0 text-[var(--muted)]" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <SeverityBadge severity={finding.severity} />
            <Badge variant="outline" className="text-[10px]">
              {finding.owasp_category}: {finding.owasp_name}
            </Badge>
            <Badge variant="outline" className="text-[10px]">
              Confidence: {finding.confidence}
            </Badge>
          </div>
          <p className="mt-1 font-medium text-sm">{finding.title}</p>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-[var(--card-border)] p-4 space-y-3 bg-[var(--background)]/50">
          <div>
            <h4 className="text-xs font-semibold uppercase text-[var(--muted)] mb-1">Description</h4>
            <p className="text-sm">{finding.description}</p>
          </div>

          {finding.evidence && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-[var(--muted)] mb-1">Evidence</h4>
              <pre className="text-xs bg-[var(--background)] border border-[var(--card-border)] rounded p-3 overflow-x-auto whitespace-pre-wrap">
                {finding.evidence}
              </pre>
            </div>
          )}

          <div>
            <h4 className="text-xs font-semibold uppercase text-[var(--muted)] mb-1">Remediation</h4>
            <p className="text-sm text-[var(--accent)]">{finding.remediation}</p>
          </div>

          <div className="flex items-center gap-1 text-xs text-[var(--muted)]">
            <ExternalLink className="h-3 w-3" />
            <span className="truncate">{finding.url}</span>
          </div>
        </div>
      )}
    </div>
  );
}
