"use client";

import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { HugeiconsIcon } from "@hugeicons/react";
import { AiChat01Icon } from "@hugeicons/core-free-icons";
import ThemeDropdown from "./ThemeDropdown";
import { getFindings } from "@/lib/api";
import type { Finding, FindingFilter } from "@/lib/types";

interface LeftSidebarProps {
  open: boolean;
  onClose: () => void;
  scanId: string | null;
}

function normalizeSeverity(
  severity: Finding["severity"]
): Exclude<FindingFilter, "all"> {
  return severity.toLowerCase() as Exclude<FindingFilter, "all">;
}

export default function LeftSidebar({
  open,
  onClose,
  scanId,
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
          <h2 className="left-sidebar-title">Summary</h2>
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
                <article key={finding.id} className="finding-card">
                  <div className="finding-card-header">
                    <div className="finding-card-main">
                      <div className="finding-card-icon" aria-hidden="true">
                        <HugeiconsIcon
                          icon={AiChat01Icon}
                          size={18}
                          strokeWidth={1.7}
                        />
                      </div>
                      <div className="finding-card-copy">
                        <p className="finding-card-title">
                          {finding.title || finding.owasp_name}
                        </p>
                        <p className="finding-card-description">
                          {finding.description}
                        </p>
                        {finding.url && (
                          <p className="finding-card-url">{finding.url}</p>
                        )}
                      </div>
                    </div>
                    <span
                      className="finding-severity-dot"
                      data-severity={finding.severity}
                      role="img"
                      aria-label={`${finding.severity} severity`}
                      title={`${finding.severity} severity`}
                    />
                  </div>
                </article>
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
