"use client";

import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import ThemeDropdown from "./ThemeDropdown";
import { getFindings } from "@/lib/api";
import type { Finding, FindingFilter } from "@/lib/types";

interface LeftSidebarProps {
  open: boolean;
  onClose: () => void;
  scanId: string | null;
  onAskAI?: (finding: Finding) => void;
}

function normalizeSeverity(
  severity: Finding["severity"]
): Exclude<FindingFilter, "all"> {
  return severity.toLowerCase() as Exclude<FindingFilter, "all">;
}

function FindingAccordion({
  finding,
  onAskAI,
}: {
  finding: Finding;
  onAskAI?: (finding: Finding) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <article className="finding-accordion">
      <div className="finding-accordion-header">
        <span
          className="finding-severity-dot"
          data-severity={finding.severity}
          title={`${finding.severity} severity`}
        />
        <button
          type="button"
          className="finding-accordion-title"
          onClick={() => setExpanded((p) => !p)}
        >
          <span>{finding.title || finding.owasp_name}</span>
          {finding.file_path && (
            <span className="finding-accordion-location">
              {finding.file_path}{finding.line_number ? `:${finding.line_number}` : ""}
            </span>
          )}
        </button>
        <div className="finding-accordion-actions">
          {onAskAI && (
            <button
              type="button"
              className="finding-ai-btn"
              title="Ask AI about this finding"
              onClick={() => onAskAI(finding)}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z" fill="currentColor" />
              </svg>
            </button>
          )}
        </div>
      </div>
      <div className={`finding-accordion-wrap${expanded ? " finding-accordion-wrap--open" : ""}`}>
        <div className="finding-accordion-body">
          <p className="finding-accordion-meta">
            {finding.owasp_category} &mdash; {finding.owasp_name} &nbsp;|&nbsp;
            Confidence: {finding.confidence}
            {finding.commit_sha && (
              <> &nbsp;|&nbsp; Commit: {finding.commit_sha.slice(0, 7)}</>
            )}
          </p>
          <p className="finding-accordion-desc">{finding.description}</p>
          {finding.code_snippet && (
            <pre className="finding-accordion-code"><code>{finding.code_snippet}</code></pre>
          )}
          {finding.url && (
            <p className="finding-accordion-url">{finding.url}</p>
          )}
          <p className="finding-accordion-remediation">
            <strong>Remediation:</strong> {finding.remediation}
          </p>
        </div>
      </div>
    </article>
  );
}

export default function LeftSidebar({
  open,
  onClose,
  scanId,
  onAskAI,
}: LeftSidebarProps) {
  const [filter, setFilter] = useState<FindingFilter>("all");
  const [findings, setFindings] = useState<Finding[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const drawerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!open) return;

    if (!scanId) {
      setFindings([]);
      setError(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    getFindings(scanId)
      .then((response) => setFindings(response.findings || []))
      .catch((err: Error) =>
        setError(err.message || "Failed to load findings")
      )
      .finally(() => setIsLoading(false));
  }, [open, scanId]);

  useEffect(() => {
    const backdrop = backdropRef.current;
    const drawer = drawerRef.current;
    if (!backdrop || !drawer) return;

    gsap.killTweensOf([backdrop, drawer]);

    if (open) {
      gsap.set(backdrop, { pointerEvents: "auto" });
      gsap.set(drawer, { pointerEvents: "auto" });
      const timeline = gsap.timeline();
      timeline.to(
        backdrop,
        { autoAlpha: 1, duration: 0.22, ease: "power2.out" },
        0
      );
      timeline.to(
        drawer,
        { x: 0, autoAlpha: 1, duration: 0.42, ease: "power3.out" },
        0
      );
      return () => {
        timeline.kill();
      };
    }

    const timeline = gsap.timeline({
      onComplete: () => {
        gsap.set(backdrop, { pointerEvents: "none" });
        gsap.set(drawer, { pointerEvents: "none" });
      },
    });
    timeline.to(
      backdrop,
      { autoAlpha: 0, duration: 0.18, ease: "power2.in" },
      0
    );
    timeline.to(
      drawer,
      { x: -56, autoAlpha: 0, duration: 0.28, ease: "power2.in" },
      0
    );

    return () => {
      timeline.kill();
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [open, onClose]);

  const visibleFindings =
    filter === "all"
      ? findings
      : findings.filter((finding) => normalizeSeverity(finding.severity) === filter);

  return (
    <>
      <div className="left-sidebar-backdrop" ref={backdropRef} onClick={onClose} />
      <aside
        className="left-sidebar"
        ref={drawerRef}
        role="dialog"
        aria-modal={open}
        aria-hidden={!open}
      >
        <div className="left-sidebar-header">
          <h2 className="left-sidebar-title">Findings</h2>
          <button type="button" className="chat-drawer-close" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="left-sidebar-body">
          <div className="left-sidebar-filter">
            <ThemeDropdown value={filter} onChange={setFilter} />
          </div>
          <div className="findings-list">
            {isLoading && (
              <p className="findings-list-message">Loading findings...</p>
            )}
            {error && (
              <p className="findings-list-message findings-list-message-error">
                {error}
              </p>
            )}
            {!isLoading && !error && findings.length === 0 && (
              <p className="findings-list-message">No findings available.</p>
            )}
            {!isLoading &&
              !error &&
              visibleFindings.map((finding) => (
                <FindingAccordion
                  key={finding.id}
                  finding={finding}
                  onAskAI={onAskAI}
                />
              ))}
            {!isLoading && !error && findings.length > 0 && visibleFindings.length === 0 && (
              <p className="findings-list-message">No findings match this filter.</p>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
