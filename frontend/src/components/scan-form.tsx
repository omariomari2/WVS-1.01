"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { createScan } from "@/lib/api";

export function ScanForm() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!url) return;
    try {
      new URL(url);
    } catch {
      setError("Please enter a valid URL (e.g., https://example.com)");
      return;
    }
    setShowModal(true);
  };

  const handleConfirm = async () => {
    setLoading(true);
    setError("");
    try {
      const scan = await createScan(url);
      router.push(`/scans/${scan.id}`);
    } catch (e: any) {
      setError(e.message || "Failed to start scan");
      setShowModal(false);
      setLoading(false);
    }
  };

  return (
    <>
      <Card className="mx-auto max-w-2xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-center gap-2 text-[var(--accent)]">
            <Shield className="h-5 w-5" />
            <h2 className="text-lg font-semibold">New Security Scan</h2>
          </div>
          <p className="text-sm text-[var(--muted)]">
            Enter the URL of the web application you want to scan for OWASP Top 10 vulnerabilities.
          </p>
          <div className="flex gap-2">
            <Input
              type="url"
              placeholder="https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              className="flex-1"
            />
            <Button type="submit" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Scan"}
            </Button>
          </div>
          {error && (
            <p className="text-sm text-[var(--destructive)]">{error}</p>
          )}
        </form>
      </Card>

      {/* Authorization Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
          <Card className="mx-4 max-w-lg space-y-4">
            <div className="flex items-center gap-2 text-yellow-500">
              <AlertTriangle className="h-6 w-6" />
              <h3 className="text-lg font-bold">Authorization Required</h3>
            </div>
            <p className="text-sm text-[var(--muted)]">
              Scanning a web application without explicit authorization is <strong className="text-[var(--foreground)]">illegal</strong> in most jurisdictions.
              By proceeding, you confirm that:
            </p>
            <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
              <li>You own the target application, <strong>or</strong></li>
              <li>You have written authorization from the owner to perform security testing</li>
            </ul>
            <div className="flex gap-3 pt-2">
              <Button
                variant="outline"
                onClick={() => setShowModal(false)}
                disabled={loading}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={handleConfirm}
                disabled={loading}
                className="flex-1"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Shield className="h-4 w-4 mr-2" />
                )}
                I Am Authorized - Begin Scan
              </Button>
            </div>
          </Card>
        </div>
      )}
    </>
  );
}
