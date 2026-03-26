"use client";

import { useState, useLayoutEffect, useCallback, useRef } from "react";
import type { Finding } from "@/lib/types";
import gsap from "gsap";
import GridBackground from "./GridBackground";
import HeroTitle from "./HeroTitle";
import ActionButton from "./ActionButton";
import InputSection from "./InputSection";
import DecorativeSvgs from "./DecorativeSvgs";
import FindingsChatDrawer from "./FindingsChatDrawer";
import LeftSidebar from "./LeftSidebar";
import RectifyDrawer from "./RectifyDrawer";
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
  const exportBtnRef = useRef<HTMLDivElement>(null);

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

  const handleRectify = useCallback(() => {
    setIsRectifyOpen((prev) => !prev);
  }, []);

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
        showToast("The scan failed, so findings export is unavailable", "error");
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
  }, [scanId, scanType]);

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

  const handleSummarize = useCallback(async () => {
    setIsLeftSidebarOpen((prev) => !prev);
  }, [uploadedHTML, scrapeMode, scrapeUrl]);

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
        visible={buttonsVisible}
        onClick={handleExploreFindings}
        disabled={loadingBtn === "first"}
      />
      <ActionButton
        label={loadingBtn === "sec" ? "Rectify..." : "Rectify"}
        variant="sec"
        visible={buttonsVisible}
        onClick={handleRectify}
        disabled={loadingBtn === "sec"}
      />
      <ActionButton
        label={loadingBtn === "third" ? "Export Logs..." : "Export Logs"}
        variant="third"
        visible={buttonsVisible}
        onClick={handleExportLogs}
        disabled={loadingBtn === "third"}
        buttonRef={exportBtnRef}
      />
      <ActionButton
        label={loadingBtn === "fourth" ? "Inspect Findings..." : "Inspect Findings"}
        variant="fourth"
        visible={buttonsVisible}
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
      />

      <DecorativeSvgs />
      <LeftSidebar
        open={isLeftSidebarOpen}
        onClose={() => setIsLeftSidebarOpen(false)}
        scanId={scanId}
        scanType={scanType}
        onAskAI={handleAskAI}
      />
      <RectifyDrawer
        open={isRectifyOpen}
        onClose={() => setIsRectifyOpen(false)}
        scanId={scanId}
        scanType={scanType}
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
