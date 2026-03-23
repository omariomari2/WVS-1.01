"use client";

import { useEffect, useState } from "react";
import { Clock, ExternalLink, Trash2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { listScans, deleteScan } from "@/lib/api";
import type { Scan } from "@/lib/types";

export default function ScansPage() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listScans().then(setScans).finally(() => setLoading(false));
  }, []);

  const handleDelete = async (id: string) => {
    await deleteScan(id);
    setScans((prev) => prev.filter((s) => s.id !== id));
  };

  const statusColor: Record<string, string> = {
    pending: "bg-yellow-500/20 text-yellow-400",
    running: "bg-blue-500/20 text-blue-400",
    completed: "bg-green-500/20 text-green-400",
    failed: "bg-red-500/20 text-red-400",
  };

  return (
    <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-bold mb-6">Scan History</h1>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse h-20" />
          ))}
        </div>
      ) : scans.length === 0 ? (
        <Card className="text-center py-12">
          <Clock className="h-12 w-12 mx-auto text-[var(--muted)] mb-3" />
          <p className="text-[var(--muted)]">No scans yet. Start your first scan from the home page.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {scans.map((scan) => (
            <Card key={scan.id} className="flex items-center justify-between p-4">
              <a href={`/scans/${scan.id}`} className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <Badge className={statusColor[scan.status]}>
                    {scan.status}
                  </Badge>
                  <span className="text-sm font-medium truncate">{scan.target_url}</span>
                </div>
                <div className="flex items-center gap-4 mt-1 text-xs text-[var(--muted)]">
                  <span>{new Date(scan.created_at).toLocaleString()}</span>
                  {scan.status === "completed" && (
                    <span>{scan.total_findings} finding{scan.total_findings !== 1 ? "s" : ""}</span>
                  )}
                </div>
              </a>
              <div className="flex items-center gap-2 ml-4">
                <a href={`/scans/${scan.id}`}>
                  <Button variant="ghost" size="sm">
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </a>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(scan.id)}
                  className="text-[var(--destructive)]"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
