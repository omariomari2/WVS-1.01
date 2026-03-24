"use client";

import { useState, useLayoutEffect, useCallback, useRef } from "react";
import gsap from "gsap";
import GridBackground from "./GridBackground";
import HeroTitle from "./HeroTitle";
import ActionButton from "./ActionButton";
import InputSection from "./InputSection";
import DecorativeSvgs from "./DecorativeSvgs";
import FindingsChatDrawer from "./FindingsChatDrawer";
import LeftSidebar from "./LeftSidebar";
import ToastContainer, { showToast } from "./Toast";
import {
  formatHTML,
  exportZip,
  exportEJSProject,
  scrapeAndExport,
} from "@/lib/api";
import { downloadBlob, DOWNLOAD_DEFAULTS } from "@/lib/download";

export default function HomePage() {
  const [uploadedHTML, setUploadedHTML] = useState("");
  const [scrapeUrl, setScrapeUrl] = useState("");
  const [inputMode, setInputMode] = useState<"upload" | "scrape">("upload");
  const [scrapeMode, setScrapeMode] = useState(false);
  const [buttonsVisible, setButtonsVisible] = useState(false);
  const [loadingBtn, setLoadingBtn] = useState<string | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(false);
  const navRef = useRef<HTMLElement>(null);

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

  const handleScrapeReady = useCallback(() => {
    setScrapeMode(true);
    setInputMode("scrape");
    setButtonsVisible(true);
    showToast("URL ready — choose an action above", "success");
  }, []);

  const handleModeChange = useCallback((mode: "upload" | "scrape") => {
    setInputMode(mode);
    if (mode === "upload") {
      setScrapeMode(false);
      setScrapeUrl("");
      setButtonsVisible(true);
      return;
    }
    setButtonsVisible(false);
  }, []);

  const handleClassifyFindings = useCallback(async () => {
  }, [uploadedHTML]);

  const handleExploreFindings = useCallback(() => {
    setIsChatOpen((prev) => !prev);
  }, []);

  const handleExportLogs = useCallback(async () => {
  }, [uploadedHTML, scrapeMode, scrapeUrl]);

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
        label={loadingBtn === "first" ? "Explore Findings..." : "Explore Findings"}
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
      />
      <ActionButton
        label={loadingBtn === "fourth" ? "Summarize..." : "Summarize"}
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
      />
      <FindingsChatDrawer
        open={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        scrapeMode={scrapeMode}
        scrapeUrl={scrapeUrl}
        hasUploadedHTML={Boolean(uploadedHTML)}
      />
      <ToastContainer />
    </>
  );
}
