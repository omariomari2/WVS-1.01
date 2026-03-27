"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type RefObject,
} from "react";
import { motion } from "motion/react";
import useMeasure from "react-use-measure";
import type { Finding, RectifyResponse } from "@/lib/types";
import {
  getFindings,
  postAiPrComment,
  postManualPrComment,
  sendFindingToClaude,
} from "@/lib/api";
import { showToast } from "./Toast";

type PopupAction = "claude" | "comment" | "study";
type PopupView = "root" | "pickFinding" | "commentMode" | "manualComment";

interface RectifyPopupProps {
  open: boolean;
  onClose: () => void;
  scanId: string | null;
  anchorRef?: RefObject<HTMLElement | null>;
}

const easeOutQuint: [number, number, number, number] = [0.23, 1, 0.32, 1];

const popupActions: Array<{
  id: PopupAction;
  label: string;
  description: string;
}> = [
  {
    id: "claude",
    label: "Send to Claude",
    description: "Pick a vulnerability and launch Claude Code in a new terminal.",
  },
  {
    id: "comment",
    label: "Comment on PR",
    description: "Post either an AI-generated or manual comment for a selected finding.",
  },
  {
    id: "study",
    label: "Study Type",
    description: "Open an OWASP-focused search for a selected vulnerability.",
  },
];

export default function RectifyPopup({
  open,
  onClose,
  scanId,
  anchorRef,
}: RectifyPopupProps) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [isLoadingFindings, setIsLoadingFindings] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<PopupAction | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [manualMode, setManualMode] = useState(false);
  const [manualComment, setManualComment] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [result, setResult] = useState<RectifyResponse | null>(null);
  const [containerRefBounds, contentBounds] = useMeasure();
  const [anchorPos, setAnchorPos] = useState<{ top: number; left: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const view: PopupView = useMemo(() => {
    if (!activeAction) return "root";
    if (activeAction !== "comment") return "pickFinding";
    if (!selectedFinding) return "pickFinding";
    return manualMode ? "manualComment" : "commentMode";
  }, [activeAction, manualMode, selectedFinding]);

  const panelWidth = useMemo(() => {
    if (view === "manualComment") return 400;
    if (view === "pickFinding") return 340;
    if (view === "commentMode") return 300;
    return 250;
  }, [view]);
  const resolvedPanelWidth =
    typeof window === "undefined"
      ? panelWidth
      : Math.min(panelWidth, Math.max(240, window.innerWidth - 16));

  const openHeight = Math.max(48, Math.ceil(contentBounds.height) + 16);
  const estimatedHeight = Math.max(openHeight, 220);

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!open) {
      setActiveAction(null);
      setSelectedFinding(null);
      setManualMode(false);
      setManualComment("");
      setActionLoading(null);
      setResult(null);
    }
  }, [open]);

  useEffect(() => {
    if (!open || !scanId) return;

    setIsLoadingFindings(true);
    setLoadError(null);

    getFindings(scanId)
      .then((response) => setFindings(response.findings || []))
      .catch((error: Error) => {
        setFindings([]);
        setLoadError(error.message || "Failed to load findings.");
      })
      .finally(() => setIsLoadingFindings(false));
  }, [open, scanId]);

  const updatePosition = useCallback(() => {
    if (!anchorRef?.current) {
      setAnchorPos(null);
      return;
    }

    const rect = anchorRef.current.getBoundingClientRect();
    let left = rect.left + rect.width / 2 - resolvedPanelWidth / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - resolvedPanelWidth - 8));

    const spaceBelow = window.innerHeight - rect.bottom;
    const top =
      spaceBelow > estimatedHeight + 8
        ? rect.bottom + 8
        : Math.max(8, rect.top - estimatedHeight - 8);

    setAnchorPos({ top, left });
  }, [anchorRef, estimatedHeight, resolvedPanelWidth]);

  useEffect(() => {
    if (!open) return;

    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);

    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open, updatePosition]);

  useEffect(() => {
    if (!open) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        handleClose();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open, handleClose]);

  useEffect(() => {
    if (!open) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") handleClose();
    };

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [open, handleClose]);

  const positionStyle: CSSProperties = anchorPos
    ? { position: "fixed", top: anchorPos.top, left: anchorPos.left, zIndex: 9999 }
    : {
        position: "fixed",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        zIndex: 9999,
      };

  const title = useMemo(() => {
    if (view === "root") return "Rectify";
    if (activeAction === "claude") return "Send to Claude";
    if (activeAction === "study") return "Study Type";
    if (view === "manualComment") return "Write My Own";
    if (view === "commentMode") return "Comment on PR";
    return "Select a Finding";
  }, [activeAction, view]);

  const subtitle = useMemo(() => {
    if (view === "root") return "Choose a PR remediation action.";
    if (view === "pickFinding") return "Select the vulnerability to use.";
    if (view === "commentMode" && selectedFinding) return selectedFinding.title || selectedFinding.owasp_name;
    if (view === "manualComment" && selectedFinding) return selectedFinding.title || selectedFinding.owasp_name;
    return null;
  }, [selectedFinding, view]);

  const handleBack = useCallback(() => {
    setResult(null);

    if (view === "manualComment") {
      setManualMode(false);
      return;
    }
    if (view === "commentMode") {
      setSelectedFinding(null);
      return;
    }
    if (view === "pickFinding") {
      setActiveAction(null);
    }
  }, [view]);

  const makeErrorResult = useCallback(
    (action: string, findingId: string, message: string): RectifyResponse => ({
      success: false,
      action,
      finding_id: findingId,
      content: null,
      diff_preview: null,
      message,
    }),
    []
  );

  const handleFindingSelection = useCallback(
    async (finding: Finding) => {
      if (!scanId || !activeAction) return;

      setSelectedFinding(finding);
      setResult(null);

      if (activeAction === "comment") {
        setManualMode(false);
        return;
      }

      if (activeAction === "study") {
        const searchTerm = (finding.owasp_name || finding.title).trim();
        const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(`site:owasp.org ${searchTerm}`)}`;
        const opened = window.open(searchUrl, "_blank", "noopener,noreferrer");
        if (!opened) {
          setResult(
            makeErrorResult(
              "study_type",
              finding.id,
              "The study tab was blocked. Please allow popups and try again."
            )
          );
          return;
        }
        showToast("Opened OWASP study tab.", "success");
        handleClose();
        return;
      }

      setActionLoading(`finding:${finding.id}`);
      try {
        const response = await sendFindingToClaude(scanId, finding.id);
        if (!response.success) {
          setResult(response);
          return;
        }
        showToast(response.message || "Claude Code launched.", "success");
        handleClose();
      } catch (error: any) {
        setResult(
          makeErrorResult(
            "send_to_claude",
            finding.id,
            error.message || "Failed to launch Claude Code."
          )
        );
      } finally {
        setActionLoading(null);
      }
    },
    [activeAction, handleClose, makeErrorResult, scanId]
  );

  const handleAiComment = useCallback(async () => {
    if (!scanId || !selectedFinding) return;

    setActionLoading("comment-ai");
    setResult(null);
    try {
      const response = await postAiPrComment(scanId, selectedFinding.id);
      if (!response.success) {
        setResult(response);
        return;
      }
      showToast(response.message || "Comment posted on PR.", "success");
      handleClose();
    } catch (error: any) {
      setResult(
        makeErrorResult(
          "pr_comment_ai",
          selectedFinding.id,
          error.message || "Failed to post AI comment."
        )
      );
    } finally {
      setActionLoading(null);
    }
  }, [handleClose, makeErrorResult, scanId, selectedFinding]);

  const handleManualComment = useCallback(async () => {
    if (!scanId || !selectedFinding) return;
    if (!manualComment.trim()) {
      setResult(
        makeErrorResult(
          "pr_comment_manual",
          selectedFinding.id,
          "Comment cannot be empty."
        )
      );
      return;
    }

    setActionLoading("comment-manual");
    setResult(null);
    try {
      const response = await postManualPrComment(
        scanId,
        selectedFinding.id,
        manualComment
      );
      if (!response.success) {
        setResult(response);
        return;
      }
      showToast(response.message || "Comment posted on PR.", "success");
      handleClose();
    } catch (error: any) {
      setResult(
        makeErrorResult(
          "pr_comment_manual",
          selectedFinding.id,
          error.message || "Failed to post manual comment."
        )
      );
    } finally {
      setActionLoading(null);
    }
  }, [handleClose, makeErrorResult, manualComment, scanId, selectedFinding]);

  const findingItems = findings.map((finding) => {
    const isBusy = actionLoading === `finding:${finding.id}`;
    return (
      <button
        key={finding.id}
        type="button"
        className="rectify-popup-finding"
        disabled={isBusy}
        onClick={() => void handleFindingSelection(finding)}
      >
        <span className="finding-severity-dot" data-severity={finding.severity} />
        <span className="rectify-popup-finding-copy">
          <span className="rectify-popup-finding-title">
            {finding.title || finding.owasp_name}
          </span>
          {finding.file_path && (
            <span className="rectify-popup-finding-location">
              {finding.file_path}
              {finding.line_number ? `:${finding.line_number}` : ""}
            </span>
          )}
        </span>
        {isBusy && <span className="rectify-popup-inline-note">Working...</span>}
      </button>
    );
  });

  return (
    <div
      ref={containerRef}
      className="rectify-popup-shell"
      style={positionStyle}
    >
      <motion.div
        initial={false}
        animate={{
          width: open ? resolvedPanelWidth : 0,
          height: open ? openHeight : 0,
          opacity: open ? 1 : 0,
          borderRadius: 16,
        }}
        transition={{
          type: "spring",
          damping: 34,
          stiffness: 380,
          mass: 0.85,
        }}
        className="rectify-popup-panel"
        style={{ overflow: "hidden" }}
      >
        <div ref={containerRefBounds} className="rectify-popup-content">
          <div className="rectify-popup-header">
            <div className="rectify-popup-header-copy">
              <div className="rectify-popup-title-row">
                {view !== "root" && (
                  <button
                    type="button"
                    className="rectify-popup-back"
                    onClick={handleBack}
                  >
                    Back
                  </button>
                )}
                <div className="rectify-popup-title">{title}</div>
              </div>
              {subtitle && <div className="rectify-popup-subtitle">{subtitle}</div>}
            </div>
            <button
              type="button"
              className="rectify-popup-close"
              onClick={handleClose}
            >
              Close
            </button>
          </div>

          {view === "root" && (
            <div className="rectify-popup-body">
              <ul className="rectify-popup-list">
                {popupActions.map((action, index) => (
                  <motion.li
                    key={action.id}
                    initial={{ opacity: 0, x: 8 }}
                    animate={{
                      opacity: open ? 1 : 0,
                      x: open ? 0 : 8,
                    }}
                    transition={{
                      delay: open ? 0.06 + index * 0.02 : 0,
                      duration: 0.15,
                      ease: easeOutQuint,
                    }}
                  >
                    <button
                      type="button"
                      className="rectify-popup-option"
                      onClick={() => {
                        setActiveAction(action.id);
                        setSelectedFinding(null);
                        setManualMode(false);
                        setManualComment("");
                        setResult(null);
                      }}
                    >
                      <span className="rectify-popup-option-label">{action.label}</span>
                      <span className="rectify-popup-option-copy">{action.description}</span>
                    </button>
                  </motion.li>
                ))}
              </ul>
            </div>
          )}

          {view === "pickFinding" && (
            <div className="rectify-popup-body">
              {isLoadingFindings && (
                <p className="rectify-popup-note">Loading findings...</p>
              )}
              {loadError && (
                <p className="rectify-popup-note rectify-popup-note-error">{loadError}</p>
              )}
              {!isLoadingFindings && !loadError && findings.length === 0 && (
                <p className="rectify-popup-note">No findings are available for this PR scan.</p>
              )}
              {!isLoadingFindings && !loadError && findings.length > 0 && (
                <div className="rectify-popup-findings">{findingItems}</div>
              )}
            </div>
          )}

          {view === "commentMode" && selectedFinding && (
            <div className="rectify-popup-body">
              <div className="rectify-popup-selected">
                <span className="finding-severity-dot" data-severity={selectedFinding.severity} />
                <div className="rectify-popup-selected-copy">
                  <div className="rectify-popup-selected-title">
                    {selectedFinding.title || selectedFinding.owasp_name}
                  </div>
                  <div className="rectify-popup-selected-meta">
                    {selectedFinding.owasp_category} - {selectedFinding.owasp_name}
                  </div>
                </div>
              </div>
              <div className="rectify-popup-inline-actions">
                <button
                  type="button"
                  className="rectify-popup-primary"
                  disabled={actionLoading === "comment-ai"}
                  onClick={() => void handleAiComment()}
                >
                  {actionLoading === "comment-ai" ? "Posting..." : "AI Comment"}
                </button>
                <button
                  type="button"
                  className="rectify-popup-secondary"
                  onClick={() => {
                    setManualMode(true);
                    setResult(null);
                  }}
                >
                  Write My Own
                </button>
              </div>
            </div>
          )}

          {view === "manualComment" && selectedFinding && (
            <div className="rectify-popup-body">
              <div className="rectify-popup-selected">
                <span className="finding-severity-dot" data-severity={selectedFinding.severity} />
                <div className="rectify-popup-selected-copy">
                  <div className="rectify-popup-selected-title">
                    {selectedFinding.title || selectedFinding.owasp_name}
                  </div>
                  <div className="rectify-popup-selected-meta">
                    {selectedFinding.file_path || "General PR comment"}
                    {selectedFinding.line_number ? `:${selectedFinding.line_number}` : ""}
                  </div>
                </div>
              </div>
              <textarea
                className="rectify-popup-textarea"
                value={manualComment}
                onChange={(event) => setManualComment(event.target.value)}
                placeholder="Write the PR comment you want to post..."
              />
              <div className="rectify-popup-inline-actions">
                <button
                  type="button"
                  className="rectify-popup-primary"
                  disabled={actionLoading === "comment-manual"}
                  onClick={() => void handleManualComment()}
                >
                  {actionLoading === "comment-manual" ? "Posting..." : "Post Comment"}
                </button>
              </div>
            </div>
          )}

          {result && !result.success && (
            <div className="rectify-popup-result rectify-popup-result-error">
              <div className="rectify-popup-result-header">
                {result.message || "Something went wrong."}
              </div>
              {result.content && (
                <pre className="rectify-popup-result-code">
                  <code>{result.content}</code>
                </pre>
              )}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
