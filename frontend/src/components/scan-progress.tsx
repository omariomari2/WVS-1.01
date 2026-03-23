"use client";

import { useEffect, useState } from "react";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { ScanProgress as ScanProgressData } from "@/lib/types";

interface ScanProgressProps {
  scanId: string;
  onComplete: () => void;
}

export function ScanProgress({ scanId, onComplete }: ScanProgressProps) {
  const [data, setData] = useState<ScanProgressData>({
    type: "progress",
    progress: 0,
    current_module: "Initializing...",
    findings_so_far: 0,
  });

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/scans/${scanId}`);

    ws.onmessage = (event) => {
      const msg: ScanProgressData = JSON.parse(event.data);
      setData(msg);
      if (msg.type === "completed" || msg.type === "error") {
        setTimeout(onComplete, 500);
      }
    };

    ws.onerror = () => {
      // Fallback: poll the API
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`/api/scans/${scanId}`);
          const scan = await res.json();
          setData({
            type: scan.status === "completed" ? "completed" : scan.status === "failed" ? "error" : "progress",
            progress: scan.progress,
            current_module: scan.current_module,
            findings_so_far: scan.total_findings,
          });
          if (scan.status === "completed" || scan.status === "failed") {
            clearInterval(interval);
            setTimeout(onComplete, 500);
          }
        } catch {}
      }, 2000);
      return () => clearInterval(interval);
    };

    return () => ws.close();
  }, [scanId, onComplete]);

  const percentage = Math.round(data.progress * 100);

  return (
    <Card className="space-y-4">
      <div className="flex items-center gap-3">
        {data.type === "completed" ? (
          <CheckCircle2 className="h-5 w-5 text-[var(--accent)]" />
        ) : data.type === "error" ? (
          <XCircle className="h-5 w-5 text-[var(--destructive)]" />
        ) : (
          <Loader2 className="h-5 w-5 animate-spin text-[var(--accent)]" />
        )}
        <div className="flex-1">
          <h3 className="font-semibold">
            {data.type === "completed"
              ? "Scan Complete"
              : data.type === "error"
              ? "Scan Failed"
              : "Scanning..."}
          </h3>
          <p className="text-sm text-[var(--muted)]">
            {data.current_module || (data.type === "completed" ? `Found ${data.total_findings || 0} findings` : "")}
          </p>
        </div>
        <span className="text-sm font-mono text-[var(--muted)]">{percentage}%</span>
      </div>
      <Progress value={percentage} />
      {data.findings_so_far !== undefined && data.type === "progress" && (
        <p className="text-xs text-[var(--muted)]">
          {data.findings_so_far} finding{data.findings_so_far !== 1 ? "s" : ""} so far
        </p>
      )}
    </Card>
  );
}
