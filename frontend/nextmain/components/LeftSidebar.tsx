"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import ThemeDropdown from "./ThemeDropdown";

interface LeftSidebarProps {
  open: boolean;
  onClose: () => void;
}

export default function LeftSidebar({ open, onClose }: LeftSidebarProps) {
  const backdropRef = useRef<HTMLDivElement>(null);
  const drawerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const backdrop = backdropRef.current;
    const drawer = drawerRef.current;
    if (!backdrop || !drawer) return;

    gsap.killTweensOf([backdrop, drawer]);

    if (open) {
      gsap.set(backdrop, { pointerEvents: "auto" });
      gsap.set(drawer, { pointerEvents: "auto" });
      const timeline = gsap.timeline();
      timeline.to(backdrop, { autoAlpha: 1, duration: 0.22, ease: "power2.out" }, 0);
      timeline.to(drawer, { x: 0, autoAlpha: 1, duration: 0.42, ease: "power3.out" }, 0);
      return () => { timeline.kill(); };
    }

    const timeline = gsap.timeline({
      onComplete: () => {
        gsap.set(backdrop, { pointerEvents: "none" });
        gsap.set(drawer, { pointerEvents: "none" });
      },
    });
    timeline.to(backdrop, { autoAlpha: 0, duration: 0.18, ease: "power2.in" }, 0);
    timeline.to(drawer, { x: -56, autoAlpha: 0, duration: 0.28, ease: "power2.in" }, 0);

    return () => { timeline.kill(); };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [open, onClose]);

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
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1.5rem' }}>
            <ThemeDropdown />
          </div>
          <p style={{ color: "var(--textDim)", fontSize: "0.9rem", lineHeight: 1.6 }}>
            Content will be displayed here.
          </p>
        </div>
      </aside>
    </>
  );
}
