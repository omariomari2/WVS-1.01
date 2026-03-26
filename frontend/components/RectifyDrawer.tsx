"use client";

import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import ReactMarkdown from "react-markdown";
import type { Finding, RectifyResponse } from "@/lib/types";
import {
  getFindings,
  rectifySend,
  rectifyApply,
  rectifyComment,
  rectifyReview,
} from "@/lib/api";

interface RectifyDrawerProps {
  open: boolean;
  onClose: () => void;
  scanId: string | null;
  scanType: "url" | "pr";
}

export default function RectifyDrawer({
  open,
  onClose,
  scanId,
  scanType,
}: RectifyDrawerProps) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchMode, setBatchMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [result, setResult] = useState<RectifyResponse | null>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const drawerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!open || !scanId) return;
    setLoading(true);
    getFindings(scanId)
      .then((res) => setFindings(res.findings || []))
      .catch(() => setFindings([]))
      .finally(() => setLoading(false));
  }, [open, scanId]);

  useEffect(() => {
    const backdrop = backdropRef.current;
    const drawer = drawerRef.current;
    if (!backdrop || !drawer) return;

    gsap.killTweensOf([backdrop, drawer]);

    if (open) {
      gsap.set(backdrop, { pointerEvents: "auto" });
      gsap.set(drawer, { pointerEvents: "auto" });
      const tl = gsap.timeline();
      tl.to(backdrop, { autoAlpha: 1, duration: 0.22, ease: "power2.out" }, 0);
      tl.to(drawer, { x: 0, autoAlpha: 1, duration: 0.42, ease: "power3.out" }, 0);
      return () => { tl.kill(); };
    }

    const tl = gsap.timeline({
      onComplete: () => {
        gsap.set(backdrop, { pointerEvents: "none" });
        gsap.set(drawer, { pointerEvents: "none" });
      },
    });
    tl.to(backdrop, { autoAlpha: 0, duration: 0.18, ease: "power2.in" }, 0);
    tl.to(drawer, { x: 56, autoAlpha: 0, duration: 0.28, ease: "power2.in" }, 0);
    return () => { tl.kill(); };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [open, onClose]);

  const selected = findings.find((f) => f.id === selectedId) || null;

  function toggleBatchSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleAction(action: string) {
    if (!scanId) return;
    setActionLoading(action);
    setResult(null);
    try {
      let res: RectifyResponse;
      if (action === "review") {
        res = await rectifyReview(scanId);
      } else if (!selectedId) {
        setResult({ success: false, action, finding_id: "", content: null, diff_preview: null, message: "Select a finding first." });
        return;
      } else if (action === "send") {
        res = await rectifySend(scanId, selectedId);
      } else if (action === "apply") {
        res = await rectifyApply(scanId, selectedId);
      } else {
        res = await rectifyComment(scanId, selectedId);
      }
      setResult(res);
    } catch (err: any) {
      setResult({ success: false, action, finding_id: selectedId || "", content: null, diff_preview: null, message: err.message });
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <>
      <div className="chat-drawer-backdrop" ref={backdropRef} onClick={onClose} />
      <aside
        className="chat-drawer"
        ref={drawerRef}
        role="dialog"
        aria-modal={open}
        aria-hidden={!open}
      >
        <div className="chat-drawer-header">
          <div className="chat-drawer-heading">
            <h2 className="chat-drawer-title">Rectify</h2>
            {scanType === "pr" && (
              <span className="rectify-badge">PR</span>
            )}
          </div>
          <button type="button" className="chat-drawer-close" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="chat-drawer-body" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {scanType === "pr" && (
            <div className="rectify-global-actions">
              <button
                type="button"
                className="rectify-action-btn rectify-action-review"
                disabled={actionLoading === "review" || findings.length === 0}
                onClick={() => handleAction("review")}
              >
                {actionLoading === "review" ? "Posting..." : "Full Security Review"}
              </button>
            </div>
          )}

          <div className="rectify-findings-list">
            {loading && <p className="findings-list-message">Loading findings...</p>}
            {!loading && findings.length === 0 && (
              <p className="findings-list-message">No findings available.</p>
            )}
            {findings.map((f) => (
              <div
                key={f.id}
                className={`rectify-finding-item ${selectedId === f.id ? "rectify-finding-selected" : ""}`}
                onClick={() => { setSelectedId(f.id); setResult(null); }}
              >
                <span className="finding-severity-dot" data-severity={f.severity} />
                <div className="rectify-finding-info">
                  <span className="rectify-finding-title">{f.title || f.owasp_name}</span>
                  {f.file_path && (
                    <span className="rectify-finding-location">
                      {f.file_path}{f.line_number ? `:${f.line_number}` : ""}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {selected && (
            <div className="rectify-detail">
              <div className="rectify-detail-meta">
                <span className="rectify-detail-severity" data-severity={selected.severity}>
                  {selected.severity}
                </span>
                <span>{selected.owasp_category} — {selected.owasp_name}</span>
                {selected.cwe && <span>{selected.cwe}</span>}
              </div>
              <p className="rectify-detail-desc">{selected.description}</p>

              {selected.code_snippet && (
                <div className="rectify-code-block">
                  <div className="rectify-code-label">Code context</div>
                  <pre><code>{selected.code_snippet}</code></pre>
                </div>
              )}

              {selected.diff_hunk && (
                <div className="rectify-code-block">
                  <div className="rectify-code-label">Diff</div>
                  <pre><code>{selected.diff_hunk}</code></pre>
                </div>
              )}

              <div className="rectify-actions">
                <div className="rectify-actions-group">
                  <div className="rectify-actions-label">Local</div>
                  <button
                    type="button"
                    className="rectify-action-btn"
                    disabled={actionLoading === "send"}
                    onClick={() => handleAction("send")}
                  >
                    {actionLoading === "send" ? "Sending..." : "Send to Cursor"}
                  </button>
                  <button
                    type="button"
                    className="rectify-action-btn"
                    disabled={actionLoading === "apply"}
                    onClick={() => handleAction("apply")}
                  >
                    {actionLoading === "apply" ? "Applying..." : "Apply Fix"}
                  </button>
                </div>
                {scanType === "pr" && (
                  <div className="rectify-actions-group">
                    <div className="rectify-actions-label">Remote</div>
                    <button
                      type="button"
                      className="rectify-action-btn"
                      disabled={actionLoading === "comment"}
                      onClick={() => handleAction("comment")}
                    >
                      {actionLoading === "comment" ? "Posting..." : "Comment on PR"}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {result && (
            <div className={`rectify-result ${result.success ? "rectify-result-ok" : "rectify-result-err"}`}>
              <div className="rectify-result-header">
                {result.success ? "Done" : "Failed"}: {result.message}
              </div>
              {result.diff_preview && (
                <div className="rectify-code-block">
                  <div className="rectify-code-label">Diff preview</div>
                  <pre><code>{result.diff_preview}</code></pre>
                </div>
              )}
              {result.content && !result.diff_preview && (
                <div className="rectify-code-block">
                  <div className="rectify-code-label">Generated content</div>
                  <div className="chat-markdown">
                    <ReactMarkdown>{result.content}</ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
