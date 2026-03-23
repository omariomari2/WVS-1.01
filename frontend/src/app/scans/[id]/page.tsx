"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Card } from "@/components/ui/card";
import { ScanProgress } from "@/components/scan-progress";
import { FindingsDashboard } from "@/components/findings-dashboard";
import { getScan } from "@/lib/api";
import type { Scan } from "@/lib/types";

export default function ScanResultsPage() {
  const params = useParams<{ id: string }>();
  const [scan, setScan] = useState<Scan | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchScan = useCallback(async () => {
    try {
      const data = await getScan(params.id);
      setScan(data);
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    fetchScan();
  }, [fetchScan]);

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <Card className="animate-pulse h-40" />
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <Card className="text-center py-12">
          <p className="text-[var(--muted)]">Scan not found.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <a href="/scans" className="inline-flex items-center gap-1 text-sm text-[var(--muted)] hover:text-[var(--foreground)]">
        <ArrowLeft className="h-4 w-4" />
        Back to scans
      </a>

      {(scan.status === "pending" || scan.status === "running") && (
        <ScanProgress scanId={scan.id} onComplete={fetchScan} />
      )}

      {scan.status === "failed" && (
        <Card className="border-[var(--destructive)]/50">
          <h3 className="font-semibold text-[var(--destructive)]">Scan Failed</h3>
          <p className="text-sm text-[var(--muted)] mt-1">{scan.error_message || "An unknown error occurred."}</p>
        </Card>
      )}

      {scan.status === "completed" && (
        <FindingsDashboard scanId={scan.id} targetUrl={scan.target_url} />
      )}
    </div>
  );
}
