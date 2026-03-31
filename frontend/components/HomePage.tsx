"use client";

import { useState, useEffect, useLayoutEffect, useCallback, useRef } from "react";
import type { Finding, ScanResponse } from "@/lib/types";
import gsap from "gsap";
import GridBackground from "./GridBackground";
import HeroTitle from "./HeroTitle";
import ActionButton from "./ActionButton";
import InputSection from "./InputSection";
import DecorativeSvgs from "./DecorativeSvgs";
import FindingsChatDrawer from "./FindingsChatDrawer";
import LeftSidebar from "./LeftSidebar";
import RectifyPopup from "./RectifyPopup";
import ExportDropdown, { type ExportFormat } from "./ExportDropdown";
import ToastContainer, { showToast } from "./Toast";
import {
  formatHTML,
  exportZip,
  exportEJSProject,
  scrapeAndExport,
  createScan,
  createPrScan,
  getScan,
  getPrScan,
  exportFindings,
} from "@/lib/api";
import { downloadBlob, DOWNLOAD_DEFAULTS } from "@/lib/download";

export default function HomePage() {
  const [uploadedHTML, setUploadedHTML] = useState("");
  const [scrapeUrl, setScrapeUrl] = useState("");
  const [prUrl, setPrUrl] = useState("");
  const [scanId, setScanId] = useState<string | null>(null);
  const [scanType, setScanType] = useState<"url" | "pr">("url");
  const [inputMode, setInputMode] = useState<"upload" | "scrape">("upload");
  const [scrapeMode, setScrapeMode] = useState(false);
  const [buttonsVisible, setButtonsVisible] = useState(false);
  const [loadingBtn, setLoadingBtn] = useState<string | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(false);
  const [isRectifyOpen, setIsRectifyOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);
  const [chatAttachedFinding, setChatAttachedFinding] = useState<Finding | null>(null);
  const navRef = useRef<HTMLElement>(null);
  const rectifyBtnRef = useRef<HTMLDivElement>(null);
  const exportBtnRef = useRef<HTMLDivElement>(null);
  const lastReportedScanStateRef = useRef<string | null>(null);
  const hasActiveOperation = Boolean(scanId);

  const getScanFailureMessage = useCallback(
    (scan: ScanResponse, fallback: string) => scan.error_message || fallback,
    []
  );

  useLayoutEffect(() => {
    if (!navRef.current) return;
    const ctx = gsap.context(() => {
      gsap.from(navRef.current?.children ?? [], {
        y: -24,
        opacity: 0,
        duration: 0.55,
        stagger: 0.07,
        ease: "power3.out",
        clearProps: "all",
      });
    }, navRef);
    return () => ctx.revert();
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const importPr = params.get("import_pr");
    if (!importPr) return;
    // Clean the URL so refreshing doesn't re-trigger
    window.history.replaceState({}, "", window.location.pathname);
    setPrUrl(importPr);
    setInputMode("scrape"); // switch to URL/PR tab
    (async () => {
      try {
        showToast("Importing PR findings...", "success");
        const scan = await createPrScan(importPr);
        setScanId(scan.id);
        setScanType("pr");
        setButtonsVisible(true);
        showToast("PR findings imported — choose an action above", "success");
      } catch (err: any) {
        showToast(err.message || "Failed to import PR scan", "error");
      }
    })();
  }, []);

  const handlePrReady = useCallback(async () => {
    if (!prUrl) {
      showToast("Please enter a PR URL first", "error");
      return;
    }
    showToast("Importing PR findings...", "success");
    try {
      const scan = await createPrScan(prUrl);
      setScanId(scan.id);
      setScanType("pr");
      setButtonsVisible(true);
      showToast("PR scan started — choose an action above", "success");
    } catch (err: any) {
      showToast(err.message || "Failed to start PR scan", "error");
    }
  }, [prUrl]);

  const handleScrapeReady = useCallback(async () => {
    if (!scrapeUrl) {
      showToast("Please enter a URL first", "error");
      return;
    }
    showToast("Starting scan...", "success");
    try {
      const scan = await createScan(scrapeUrl);
      setScanId(scan.id);
      setScanType("url");
      setScrapeMode(true);
      setInputMode("scrape");
      setButtonsVisible(true);
      showToast("Scan started — choose an action above", "success");
    } catch (err: any) {
      showToast(err.message || "Failed to start scan", "error");
    }
  }, [scrapeUrl]);

  const handleModeChange = useCallback((mode: "upload" | "scrape") => {
    setInputMode(mode);
    setButtonsVisible(false);
  }, []);

  const handleEndOperation = useCallback(() => {
    setUploadedHTML("");
    setScrapeUrl("");
    setPrUrl("");
    setScanId(null);
    setScanType("url");
    setInputMode("upload");
    setScrapeMode(false);
    setButtonsVisible(false);
    setLoadingBtn(null);
    setIsChatOpen(false);
    setIsLeftSidebarOpen(false);
    setIsRectifyOpen(false);
    setIsExportOpen(false);
    setExportingFormat(null);
    setChatAttachedFinding(null);
    lastReportedScanStateRef.current = null;
    showToast("Operation ended. Ready for a new scan.", "info");
  }, []);

  useEffect(() => {
    if (!scanId) {
      lastReportedScanStateRef.current = null;
      return;
    }

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    const pollScan = async () => {
      try {
        const scan =
          scanType === "pr" ? await getPrScan(scanId) : await getScan(scanId);
        if (cancelled) return;

        const stateKey = `${scan.id}:${scan.status}:${scan.error_message || ""}`;
        if (scan.status === "failed") {
          if (lastReportedScanStateRef.current !== stateKey) {
            showToast(
              getScanFailureMessage(scan, "The scan failed."),
              "error"
            );
            lastReportedScanStateRef.current = stateKey;
          }
          return;
        }

        lastReportedScanStateRef.current = stateKey;
        if (scan.status !== "completed") {
          timeoutId = setTimeout(pollScan, 3000);
        }
      } catch {
        if (!cancelled) {
          timeoutId = setTimeout(pollScan, 5000);
        }
      }
    };

    void pollScan();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [getScanFailureMessage, scanId, scanType]);

  useEffect(() => {
    if (scanType !== "pr" && isRectifyOpen) {
      setIsRectifyOpen(false);
    }
  }, [isRectifyOpen, scanType]);

  const handleRectify = useCallback(async () => {
    if (!scanId || scanType !== "pr") {
      showToast("Rectify is available only for PR scans.", "info");
      return;
    }

    setLoadingBtn("sec");
    try {
      const scan = await getPrScan(scanId);
      if (scan.status === "failed") {
        showToast(
          getScanFailureMessage(
            scan,
            "The PR scan failed, so rectify actions are unavailable."
          ),
          "error"
        );
        return;
      }
      if (scan.status !== "completed") {
        showToast("PR findings are still loading. Try Rectify again once the scan completes.", "info");
        return;
      }
      setIsExportOpen(false);
      setIsRectifyOpen((prev) => !prev);
    } catch (err: any) {
      showToast(err.message || "Failed to open rectify actions", "error");
    } finally {
      setLoadingBtn(null);
    }
  }, [getScanFailureMessage, scanId, scanType]);

  const handleExploreFindings = useCallback(() => {
    setIsChatOpen((prev) => !prev);
  }, []);

  const handleAskAI = useCallback((finding: Finding) => {
    setChatAttachedFinding(finding);
    setIsChatOpen(true);
  }, []);

  const handleExportLogs = useCallback(async () => {
    if (!scanId) {
      showToast("Run a scan first before exporting", "error");
      return;
    }
    setLoadingBtn("third");
    try {
      const scan = scanType === "pr" ? await getPrScan(scanId) : await getScan(scanId);
      if (scan.status === "failed") {
        showToast(
          getScanFailureMessage(
            scan,
            "The scan failed, so findings export is unavailable"
          ),
          "error"
        );
        return;
      }
      if (scan.status !== "completed") {
        showToast("Scan is still running. Try exporting again when it completes", "info");
        return;
      }
      setIsExportOpen((prev) => !prev);
    } catch (err: any) {
      showToast(err.message || "Failed to check scan status", "error");
    } finally {
      setLoadingBtn(null);
    }
  }, [getScanFailureMessage, scanId, scanType]);

  const handleExportSelect = useCallback(
    async (format: ExportFormat) => {
      if (!scanId) return;
      setExportingFormat(format);
      try {
        const { blob, filename } = await exportFindings(scanId, format);
        const result = await downloadBlob(
          blob,
          filename,
          format,
          DOWNLOAD_DEFAULTS.useFilePicker
        );
        if (result === "canceled") {
          showToast("Export canceled", "info");
          return;
        }
        showToast(`Exported as ${format.toUpperCase()}`, "success");
        setIsExportOpen(false);
      } catch (err: any) {
        showToast(err.message || "Export failed", "error");
      } finally {
        setExportingFormat(null);
      }
    },
    [scanId]
  );

  const handleSummarize = useCallback(() => {
    setIsLeftSidebarOpen((prev) => !prev);
  }, []);

  return (
    <>
      <nav ref={navRef}>
        <p className="sitename">WVS</p>
      </nav>

      <GridBackground />
      <HeroTitle />

      <ActionButton
        label={loadingBtn === "first" ? "Ask Agent..." : "Ask Agent"}
        variant="first"
        visible={buttonsVisible || hasActiveOperation}
        onClick={handleExploreFindings}
        disabled={loadingBtn === "first"}
      />
      <ActionButton
        label={loadingBtn === "sec" ? "Rectify..." : "Rectify"}
        variant="sec"
        visible={(buttonsVisible || hasActiveOperation) && scanType === "pr"}
        onClick={handleRectify}
        disabled={loadingBtn === "sec"}
        buttonRef={rectifyBtnRef}
      />
      <ActionButton
        label={loadingBtn === "third" ? "Export Logs..." : "Export Logs"}
        variant="third"
        visible={buttonsVisible || hasActiveOperation}
        onClick={handleExportLogs}
        disabled={loadingBtn === "third"}
        buttonRef={exportBtnRef}
      />
      <ActionButton
        label={loadingBtn === "fourth" ? "Inspect Findings..." : "Inspect Findings"}
        variant="fourth"
        visible={buttonsVisible || hasActiveOperation}
        onClick={handleSummarize}
        disabled={loadingBtn === "fourth"}
      />

      <InputSection
        onScrapeReady={handleScrapeReady}
        scrapeUrl={scrapeUrl}
        onScrapeUrlChange={setScrapeUrl}
        onPrReady={handlePrReady}
        prUrl={prUrl}
        onPrUrlChange={setPrUrl}
        mode={inputMode}
        onModeChange={handleModeChange}
        hasActiveOperation={hasActiveOperation}
        onEndOperation={handleEndOperation}
      />

      <DecorativeSvgs />
      <LeftSidebar
        open={isLeftSidebarOpen}
        onClose={() => setIsLeftSidebarOpen(false)}
        scanId={scanId}
        onAskAI={handleAskAI}
      />
      <RectifyPopup
        open={isRectifyOpen}
        onClose={() => setIsRectifyOpen(false)}
        scanId={scanId}
        anchorRef={rectifyBtnRef}
      />
      <FindingsChatDrawer
        open={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        scrapeMode={scrapeMode}
        scrapeUrl={scrapeUrl}
        hasUploadedHTML={Boolean(uploadedHTML)}
        scanId={scanId}
        attachedFinding={chatAttachedFinding}
        onClearAttachedFinding={() => setChatAttachedFinding(null)}
      />
      <ExportDropdown
        open={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        onSelect={handleExportSelect}
        loading={exportingFormat}
        anchorRef={exportBtnRef}
      />
      <ToastContainer />
    </>
  );
}
