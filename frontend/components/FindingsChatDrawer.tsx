"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import gsap from "gsap";
import ReactMarkdown from "react-markdown";
import type { Finding } from "@/lib/types";

type Message = {
  id: number;
  role: "assistant" | "user";
  text: string;
};

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
    if (!open) return;
    setMessages([{ id: 1, role: "assistant", text: starterMessage }]);
  }, [open, starterMessage]);

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

      if (!res.body) throw new Error("No response body");
      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let fullText = "";
      let isFirstChunk = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            let data = line.slice(6);
            if (data === "[DONE]") break;

            data = data.replace(/\\n/g, "\n");
            if (isFirstChunk) {
              fullText = data;
              isFirstChunk = false;
            } else {
              fullText += data;
            }

            setMessages((prev) => prev.map(m => m.id === assistantId ? { ...m, text: fullText } : m));
          }
        }
      }
    } catch (err: any) {
      setMessages((prev) => prev.map(m => m.id === assistantId ? { ...m, text: err.message || "Error connecting to AI analyst." } : m));
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
                      <ReactMarkdown>{message.text}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="chat-message-content">
                  <div className="chat-message-label">You</div>
                  <div className="chat-message-bubble">{message.text}</div>
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
