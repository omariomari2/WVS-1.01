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

const SAMPLE_FINDINGS: Finding[] = [
  {
    id: "sample-finding-1",
    scan_id: "sample-scan",
    owasp_category: "A03",
    owasp_name: "Injection",
    severity: "Critical",
    title: "Unsanitized query parameter reaches SQL execution path",
    description:
      "A user-controlled `search` parameter appears to flow into a raw SQL query without parameterization, making the endpoint vulnerable to injection.",
    evidence: "Request parameter `search` is interpolated into a database query.",
    url: "https://demo.venom.local/admin/users?search=' OR 1=1 --",
    remediation:
      "Switch to parameterized queries and validate the incoming parameter before it reaches the query builder.",
    confidence: "High",
    created_at: "2026-03-27T12:00:00.000Z",
    file_path: "frontend/app/api/admin/users/route.ts",
    line_number: 42,
    commit_sha: "a1b2c3d4e5f6g7h8i9j0",
    code_snippet:
      "const query = `SELECT * FROM users WHERE email LIKE '%${search}%'`;",
    diff_hunk: null,
    rule_id: "sample.sql-injection",
    cwe: "CWE-89",
  },
  {
    id: "sample-finding-2",
    scan_id: "sample-scan",
    owasp_category: "A01",
    owasp_name: "Broken Access Control",
    severity: "High",
    title: "Admin diagnostics panel exposed to authenticated non-admin users",
    description:
      "The diagnostics route is reachable after sign-in, but the UI and handler do not enforce an admin-specific guard before rendering sensitive system data.",
    evidence: "Role check is missing before the diagnostics panel is mounted.",
    url: "https://demo.venom.local/internal/diagnostics",
    remediation:
      "Require an admin role check in both the route guard and the server-side handler before returning diagnostics data.",
    confidence: "Medium",
    created_at: "2026-03-27T12:05:00.000Z",
    file_path: "frontend/components/admin/DiagnosticsPanel.tsx",
    line_number: 88,
    commit_sha: "f1e2d3c4b5a697887766",
    code_snippet:
      "if (session?.user) {\n  return <DiagnosticsPanel metrics={metrics} />;\n}",
    diff_hunk: null,
    rule_id: "sample.missing-role-check",
    cwe: "CWE-285",
  },
  {
    id: "sample-finding-3",
    scan_id: "sample-scan",
    owasp_category: "A05",
    owasp_name: "Security Misconfiguration",
    severity: "Medium",
    title: "Sensitive debug banner leaks deployment metadata in production",
    description:
      "A production-visible debug banner reveals environment identifiers and internal release metadata that should stay hidden from general users.",
    evidence: "Build metadata is rendered into a client-facing status banner.",
    url: "https://demo.venom.local",
    remediation:
      "Gate diagnostic UI behind a development-only flag and strip internal metadata from production builds.",
    confidence: "Medium",
    created_at: "2026-03-27T12:10:00.000Z",
    file_path: "frontend/components/StatusBanner.tsx",
    line_number: 17,
    commit_sha: null,
    code_snippet:
      "<span>{process.env.NEXT_PUBLIC_RELEASE_SHA} | {process.env.NEXT_PUBLIC_ENV_NAME}</span>",
    diff_hunk: null,
    rule_id: "sample.debug-banner",
    cwe: "CWE-200",
  },
  {
    id: "sample-finding-4",
    scan_id: "sample-scan",
    owasp_category: "A09",
    owasp_name: "Security Logging and Monitoring Failures",
    severity: "Low",
    title: "Client-side auth failure path does not emit an audit event",
    description:
      "Repeated login failures are surfaced to the user, but the client flow does not appear to trigger a corresponding audit trail for downstream monitoring.",
    evidence: "No telemetry or audit helper is called in the failed authentication branch.",
    url: "https://demo.venom.local/login",
    remediation:
      "Emit a structured security event on failed login attempts so monitoring can detect brute-force patterns.",
    confidence: "Low",
    created_at: "2026-03-27T12:15:00.000Z",
    file_path: "frontend/app/(auth)/login/page.tsx",
    line_number: 133,
    commit_sha: null,
    code_snippet:
      "catch (error) {\n  setError(\"Invalid email or password\");\n}",
    diff_hunk: null,
    rule_id: "sample.missing-audit-event",
    cwe: "CWE-778",
  },
  {
    id: "sample-finding-5",
    scan_id: "sample-scan",
    owasp_category: "A06",
    owasp_name: "Vulnerable and Outdated Components",
    severity: "Informational",
    title: "Legacy client bundle fingerprint detected in static assets",
    description:
      "A legacy bundle marker was detected in the published assets. This is not immediately exploitable, but it is useful for testing the informational state and may indicate cleanup work is still pending.",
    evidence:
      "Static asset naming suggests an older client bundle is still being shipped.",
    url: "https://demo.venom.local/_next/static/chunks/legacy-dashboard.js",
    remediation:
      "Review the production bundle output and remove stale artifacts that are no longer referenced by the current build.",
    confidence: "Low",
    created_at: "2026-03-27T12:18:00.000Z",
    file_path: "frontend/.next/static/chunks/legacy-dashboard.js",
    line_number: null,
    commit_sha: null,
    code_snippet: null,
    diff_hunk: null,
    rule_id: "sample.legacy-bundle-marker",
    cwe: "CWE-1104",
  },
];

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
        <button
          type="button"
          className="finding-accordion-trigger"
          aria-expanded={expanded}
          onClick={() => setExpanded((previous) => !previous)}
        >
          <span
            className="finding-accordion-title"
            data-severity={finding.severity}
          >
            {finding.title || finding.owasp_name}
          </span>
          {finding.file_path && (
            <span className="finding-accordion-location">
              {finding.file_path}
              {finding.line_number ? `:${finding.line_number}` : ""}
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
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z"
                  fill="currentColor"
                />
              </svg>
            </button>
          )}
        </div>
      </div>
      <div
        className={`finding-accordion-wrap${expanded ? " finding-accordion-wrap--open" : ""}`}
      >
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
            <pre className="finding-accordion-code">
              <code>{finding.code_snippet}</code>
            </pre>
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
      .catch((err: Error) => setError(err.message || "Failed to load findings"))
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

  const usingMockFindings =
    !isLoading && !error && findings.length === 0 && SAMPLE_FINDINGS.length > 0;
  const displayFindings = usingMockFindings ? SAMPLE_FINDINGS : findings;
  const visibleFindings =
    filter === "all"
      ? displayFindings
      : displayFindings.filter(
          (finding) => normalizeSeverity(finding.severity) === filter
        );

  return (
    <>
      <div
        className="left-sidebar-backdrop"
        ref={backdropRef}
        onClick={onClose}
      />
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
          {usingMockFindings && (
            <p className="findings-list-note">
              Sample Findings
              <span className="findings-list-note-copy">
                Showing temporary hardcoded content because live findings are not
                available yet.
              </span>
            </p>
          )}
          <div className="findings-list">
            {isLoading && (
              <p className="findings-list-message">Loading findings...</p>
            )}
            {error && (
              <p className="findings-list-message findings-list-message-error">
                {error}
              </p>
            )}
            {!isLoading && !error && displayFindings.length === 0 && (
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
            {!isLoading &&
              !error &&
              displayFindings.length > 0 &&
              visibleFindings.length === 0 && (
                <p className="findings-list-message">
                  No findings match this filter.
                </p>
              )}
          </div>
        </div>
      </aside>
    </>
  );
}
