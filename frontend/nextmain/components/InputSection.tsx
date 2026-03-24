"use client";

import ActionButton from "./ActionButton";

interface InputSectionProps {
  onScrapeReady: () => void;
  scrapeUrl: string;
  onScrapeUrlChange: (url: string) => void;
  mode: "upload" | "scrape";
  onModeChange: (mode: "upload" | "scrape") => void;
}

export default function InputSection({
  onScrapeReady,
  scrapeUrl,
  onScrapeUrlChange,
  mode,
  onModeChange,
}: InputSectionProps) {
  function handleScrapeClick() {
  }

  return (
    <div className="input-section">
      <div className="input-mode-toggle">
        <button
          className={`mode-btn ${mode === "upload" ? "mode-btn-active" : ""}`}
          onClick={() => onModeChange("upload")}
        >
          Upload HTML
        </button>
        <button
          className={`mode-btn ${mode === "scrape" ? "mode-btn-active" : ""}`}
          onClick={() => onModeChange("scrape")}
        >
          Scrape URL
        </button>
      </div>
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
            onClick={handleScrapeClick}
          />
        </div>
      )}
    </div>
  );
}
