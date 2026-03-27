"use client";

import ActionButton from "./ActionButton";

interface InputSectionProps {
  onScrapeReady: () => void;
  scrapeUrl: string;
  onScrapeUrlChange: (url: string) => void;
  onPrReady: () => void;
  prUrl: string;
  onPrUrlChange: (url: string) => void;
  mode: "upload" | "scrape";
  onModeChange: (mode: "upload" | "scrape") => void;
}

export default function InputSection({
  onScrapeReady,
  scrapeUrl,
  onScrapeUrlChange,
  onPrReady,
  prUrl,
  onPrUrlChange,
  mode,
  onModeChange,
}: InputSectionProps) {
  return (
    <div className="input-section">
      <div className="input-mode-toggle">
        <button
          className={`mode-btn ${mode === "upload" ? "mode-btn-active" : ""}`}
          onClick={() => onModeChange("upload")}
        >
          Check PR
        </button>
        <button
          className={`mode-btn ${mode === "scrape" ? "mode-btn-active" : ""}`}
          onClick={() => onModeChange("scrape")}
        >
          Scrape URL
        </button>
      </div>
      {mode === "upload" && (
        <div className="scrape-input-area">
          <input
            id="pr-url-input"
            type="url"
            placeholder="https://github.com/owner/repo/pull/123"
            autoComplete="off"
            spellCheck={false}
            value={prUrl}
            onChange={(e) => onPrUrlChange(e.target.value)}
          />
          <ActionButton
            label="Scan PR"
            variant="scrape"
            onClick={onPrReady}
          />
        </div>
      )}
      {mode === "scrape" && (
        <div className="scrape-input-area">
          <input
            id="scrape-url-input"
            type="url"
            placeholder="https://example.com"
            autoComplete="off"
            spellCheck={false}
            value={scrapeUrl}
            onChange={(e) => onScrapeUrlChange(e.target.value)}
          />
          <ActionButton
            label="Scrape"
            variant="scrape"
            onClick={onScrapeReady}
          />
        </div>
      )}
    </div>
  );
}
