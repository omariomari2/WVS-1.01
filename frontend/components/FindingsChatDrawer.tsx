"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import gsap from "gsap";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import type { Finding } from "@/lib/types";

type Message = {
  id: number;
  role: "assistant" | "user";
  text: string;
};

type ParsedSseEvent = {
  event: string;
  data: string;
};

const markdownComponents: Components = {
  p({ children }) {
    return <p className="chat-markdown-paragraph">{children}</p>;
  },
  ul({ children }) {
    return <ul className="chat-markdown-list chat-markdown-list-unordered">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="chat-markdown-list chat-markdown-list-ordered">{children}</ol>;
  },
  li({ children }) {
    return <li className="chat-markdown-list-item">{children}</li>;
  },
  h1({ children }) {
    return <h1 className="chat-markdown-heading chat-markdown-heading-1">{children}</h1>;
  },
  h2({ children }) {
    return <h2 className="chat-markdown-heading chat-markdown-heading-2">{children}</h2>;
  },
  h3({ children }) {
    return <h3 className="chat-markdown-heading chat-markdown-heading-3">{children}</h3>;
  },
  h4({ children }) {
    return <h4 className="chat-markdown-heading chat-markdown-heading-4">{children}</h4>;
  },
  strong({ children }) {
    return <strong className="chat-markdown-strong">{children}</strong>;
  },
  em({ children }) {
    return <em className="chat-markdown-emphasis">{children}</em>;
  },
  blockquote({ children }) {
    return <blockquote className="chat-markdown-quote">{children}</blockquote>;
  },
  hr() {
    return <hr className="chat-markdown-divider" />;
  },
  pre({ children }) {
    return <pre className="chat-markdown-pre">{children}</pre>;
  },
  code({ className, children, ...props }) {
    return (
      <code
        className={className ? `chat-markdown-code ${className}` : "chat-markdown-code"}
        {...props}
      >
        {children}
      </code>
    );
  },
  table({ children }) {
    return (
      <div className="chat-markdown-table-wrap">
        <table className="chat-markdown-table">{children}</table>
      </div>
    );
  },
  thead({ children }) {
    return <thead className="chat-markdown-thead">{children}</thead>;
  },
  tbody({ children }) {
    return <tbody className="chat-markdown-tbody">{children}</tbody>;
  },
  tr({ children }) {
    return <tr className="chat-markdown-row">{children}</tr>;
  },
  th({ children }) {
    return <th className="chat-markdown-cell chat-markdown-cell-head">{children}</th>;
  },
  td({ children }) {
    return <td className="chat-markdown-cell">{children}</td>;
  },
  a({ children, href, ...props }) {
    return (
      <a
        className="chat-markdown-link"
        href={href}
        rel="noreferrer"
        target="_blank"
        {...props}
      >
        {children}
      </a>
    );
  },
};

function normalizeAssistantMarkdown(text: string): string {
  // Keep model formatting intact. Only normalize line endings and strip emojis.
  const cleaned = text
    .replace(/\r\n?/g, "\n")
    .replace(/[\p{Extended_Pictographic}\uFE0F]/gu, "")
    .replace(/\u0000/g, "");

  const hasStructuredMarkdown =
    /(^|\n)\s*(#{1,6}\s|[-*+]\s|\d+\.\s|>\s|```|\|)/m.test(cleaned);
  const hasAnyNewline = cleaned.includes("\n");

  if (hasStructuredMarkdown || hasAnyNewline || cleaned.length < 220) {
    return cleaned;
  }

  // Fallback for dense plain-text replies: add light sentence breaks for readability.
  return cleaned
    .replace(/([.!?])\s+(?=[A-Za-z])/g, "$1\n")
    .replace(/:\s+(?=[A-Za-z])/g, ":\n");
}

function parseSseEvent(block: string): ParsedSseEvent | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim() || "message";
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.startsWith("data: ") ? line.slice(6) : line.slice(5));
    }
  }

  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

async function readChatError(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    const payload = await response.json().catch(() => null);
    const detail =
      payload?.detail || payload?.message || payload?.error || payload?.title;
    if (typeof detail === "string" && detail.trim()) {
      return detail.trim();
    }
  }

  const text = await response.text().catch(() => "");
  if (text.trim()) return text.trim();

  return `Chat request failed (${response.status} ${response.statusText}).`;
}

interface FindingsChatDrawerProps {
  open: boolean;
  onClose: () => void;
  scrapeMode: boolean;
  scrapeUrl: string;
  hasUploadedHTML: boolean;
  scanId: string | null;
  attachedFinding?: Finding | null;
  onClearAttachedFinding?: () => void;
}

export default function FindingsChatDrawer({
  open,
  onClose,
  scrapeMode,
  scrapeUrl,
  hasUploadedHTML,
  scanId,
  attachedFinding: externalFinding,
  onClearAttachedFinding,
}: FindingsChatDrawerProps) {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [localFinding, setLocalFinding] = useState<Finding | null>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const drawerRef = useRef<HTMLElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const previousScanIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (externalFinding) {
      setLocalFinding(externalFinding);
      onClearAttachedFinding?.();
    }
  }, [externalFinding, onClearAttachedFinding]);

  useEffect(() => {
    if (!open) setLocalFinding(null);
  }, [open]);

  const starterMessage = useMemo(() => {
    if (scrapeMode && scrapeUrl.trim()) {
      return `WVS is ready to review ${scrapeUrl}. Ask for high-signal findings, suspicious flows, exposed inputs, client-side logic, or where to investigate next.`;
    }

    if (hasUploadedHTML) {
      return "WVS is ready to inspect the uploaded frontend. Ask about forms, scripts, routes, inputs, structure, or anything that looks worth validating.";
    }

    return "WVS chat is standing by. Upload HTML or provide a scrape target, then ask for findings, risky patterns, or deeper frontend investigation paths.";
  }, [hasUploadedHTML, scrapeMode, scrapeUrl]);

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
      return () => { timeline.kill(); };
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
      { x: 56, autoAlpha: 0, duration: 0.28, ease: "power2.in" },
      0
    );

    return () => { timeline.kill(); };
  }, [open]);

  useEffect(() => {
    if (previousScanIdRef.current === scanId) return;

    previousScanIdRef.current = scanId;

    if (!scanId) {
      setMessages([]);
      setDraft("");
      setLocalFinding(null);
      return;
    }

    setMessages([{ id: Date.now(), role: "assistant", text: starterMessage }]);
    setDraft("");
    setLocalFinding(null);
  }, [scanId, starterMessage]);

  useEffect(() => {
    if (!open || !bodyRef.current) return;
    bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages, open]);

  useEffect(() => {
    if (!open) return;
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [open, onClose]);

  function buildMessageForBackend(userText: string, finding: Finding | null): string {
    if (!finding) return userText;
    const parts = [
      `[Context: "${finding.title}" | ${finding.severity} | ${finding.owasp_category} - ${finding.owasp_name}]`,
      finding.description,
    ];
    if (finding.evidence) parts.push(`Evidence: ${finding.evidence}`);
    if (finding.url) parts.push(`URL: ${finding.url}`);
    parts.push("---", userText);
    return parts.join("\n");
  }

  async function handleSend() {
    const userText = draft.trim();
    if (!userText) return;

    const backendMessage = buildMessageForBackend(userText, localFinding);
    const userMessage: Message = { id: Date.now(), role: "user", text: userText };
    const assistantId = Date.now() + 1;
    const assistantMessage: Message = { id: assistantId, role: "assistant", text: "..." };

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setDraft("");
    setLocalFinding(null);

    if (!scanId) {
      setMessages((prev) => prev.map(m => m.id === assistantId ? { ...m, text: "No active scan found to chat about." } : m));
      return;
    }

    try {
      const res = await fetch(`http://localhost:8000/api/scans/${scanId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: backendMessage }),
      });

      if (!res.ok) {
        throw new Error(await readChatError(res));
      }

      if (!res.body) {
        throw new Error("The chat service returned an empty response.");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let fullText = "";
      let isFirstChunk = true;
      let isDone = false;

      while (!isDone) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

        let boundaryIndex = buffer.indexOf("\n\n");
        while (boundaryIndex !== -1) {
          const rawEvent = buffer.slice(0, boundaryIndex).replace(/\r/g, "");
          buffer = buffer.slice(boundaryIndex + 2);

          const parsedEvent = parseSseEvent(rawEvent);
          if (parsedEvent) {
            if (parsedEvent.event === "error") {
              let message = parsedEvent.data;
              try {
                const payload = JSON.parse(parsedEvent.data);
                if (typeof payload?.message === "string" && payload.message.trim()) {
                  message = payload.message.trim();
                }
              } catch {
                // Fall back to the raw SSE data when the payload is plain text.
              }
              throw new Error(message || "The AI analyst returned an error.");
            }

            if (parsedEvent.data === "[DONE]") {
              isDone = true;
              break;
            }

            if (isFirstChunk) {
              fullText = parsedEvent.data;
              isFirstChunk = false;
            } else {
              fullText += parsedEvent.data;
            }

            setMessages((prev) =>
              prev.map((message) =>
                message.id === assistantId
                  ? { ...message, text: fullText }
                  : message
              )
            );
          }

          boundaryIndex = buffer.indexOf("\n\n");
        }

        if (done) break;
      }
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                text: err.message || "Error connecting to AI analyst.",
              }
            : message
        )
      );
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    handleSend();
  }

  return (
    <>
      <div className="chat-drawer-backdrop" ref={backdropRef} onClick={onClose} />
      <aside
        className="chat-drawer"
        ref={drawerRef}
        role="dialog"
        aria-modal={open}
        aria-hidden={!open}
      >
        <div className="chat-drawer-header">
          <div className="chat-drawer-heading">
            <h2 className="chat-drawer-title">WVS Analyst</h2>
          </div>
          <button type="button" className="chat-drawer-close" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="chat-drawer-body" ref={bodyRef}>
          {messages.map((message) => (
            <div
              key={message.id}
              className={`chat-message chat-message-${message.role}`}
            >
              {message.role === "assistant" ? (
                <div className="chat-message-row">
                  <div className="chat-message-avatar">W</div>
                  <div className="chat-message-content">
                    <div className="chat-message-label">WVS</div>
                    <div className="chat-message-bubble chat-markdown">
                      <ReactMarkdown
                        components={markdownComponents}
                        remarkPlugins={[remarkGfm, remarkBreaks]}
                      >
                        {normalizeAssistantMarkdown(message.text)}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="chat-message-row">
                  <div className="chat-message-content">
                    <div className="chat-message-label">You</div>
                    <div className="chat-message-bubble">{message.text}</div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="chat-drawer-footer">
          <div className="chat-composer">
            {localFinding && (
              <div className="chat-context-card" data-severity={localFinding.severity}>
                <span
                  className="chat-context-dot"
                  data-severity={localFinding.severity}
                />
                <span className="chat-context-title">
                  {localFinding.title || localFinding.owasp_name}
                </span>
                <button
                  type="button"
                  className="chat-context-dismiss"
                  onClick={() => setLocalFinding(null)}
                  aria-label="Remove context"
                >
                  &times;
                </button>
              </div>
            )}
            <textarea
              className="chat-input"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                localFinding
                  ? "Ask something about this finding..."
                  : "Ask WVS about findings, inputs, scripts, flows, or risk signals"
              }
            />
            <div className="chat-composer-actions">
              <div className="chat-composer-note">
                WVS suggestions are directional. Validate important findings before acting.
              </div>
              <button type="button" className="chat-send-btn" onClick={handleSend}>
                Send
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}

