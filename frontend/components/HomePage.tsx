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
import ExportDropdown, { type ExportFormat } from "./ExportDropdown";
import ToastContainer, { showToast } from "./Toast";
import {
  formatHTML,
  exportZip,
  exportEJSProject,
  scrapeAndExport,
  createScan,
  getScan,
  exportFindings,
} from "@/lib/api";
import { downloadBlob, DOWNLOAD_DEFAULTS } from "@/lib/download";

export default function HomePage() {
  const [uploadedHTML, setUploadedHTML] = useState("");
  const [scrapeUrl, setScrapeUrl] = useState("");
  const [scanId, setScanId] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<"upload" | "scrape">("upload");
  const [scrapeMode, setScrapeMode] = useState(false);
  const [buttonsVisible, setButtonsVisible] = useState(false);
  const [loadingBtn, setLoadingBtn] = useState<string | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(false);
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

  const handleScrapeReady = useCallback(async () => {
    if (!scrapeUrl) {
      showToast("Please enter a URL first", "error");
      return;
    }
    showToast("Starting scan...", "success");
    try {
      const scan = await createScan(scrapeUrl);
      setScanId(scan.id);
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

  const handleClassifyFindings = useCallback(async () => {
  }, [uploadedHTML]);

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
      const scan = await getScan(scanId);
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
  }, [scanId]);

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
        label={loadingBtn === "sec" ? "Classify Findings..." : "Classify Findings"}
        variant="sec"
        visible={buttonsVisible}
        onClick={handleClassifyFindings}
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
        mode={inputMode}
        onModeChange={handleModeChange}
      />

      <DecorativeSvgs />
      <LeftSidebar
        open={isLeftSidebarOpen}
        onClose={() => setIsLeftSidebarOpen(false)}
        scanId={scanId}
        onAskAI={handleAskAI}
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
