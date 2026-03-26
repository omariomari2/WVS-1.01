"use client";

import { useState, useRef, useEffect, useCallback, type RefObject } from "react";
import { motion } from "motion/react";
import useMeasure from "react-use-measure";

const exportFormats = [
  { id: "pdf", label: "PDF Report" },
  { id: "csv", label: "CSV" },
  { id: "json", label: "JSON" },
  { id: "md", label: "Markdown" },
] as const;

export type ExportFormat = (typeof exportFormats)[number]["id"];

interface ExportDropdownProps {
  open: boolean;
  onClose: () => void;
  onSelect: (format: ExportFormat) => void;
  loading?: string | null;
  anchorRef?: RefObject<HTMLElement | null>;
}

const easeOutQuint: [number, number, number, number] = [0.23, 1, 0.32, 1];

export default function ExportDropdown({
  open,
  onClose,
  onSelect,
  loading,
  anchorRef,
}: ExportDropdownProps) {
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [contentRef, contentBounds] = useMeasure();
  const [anchorPos, setAnchorPos] = useState<{ top: number; left: number } | null>(null);
  const estimatedHeight = exportFormats.length * 32 + 40;

  const updatePosition = useCallback(() => {
    if (!anchorRef?.current) {
      setAnchorPos(null);
      return;
    }
    const rect = anchorRef.current.getBoundingClientRect();
    const dropdownWidth = 180;
    let left = rect.left + rect.width / 2 - dropdownWidth / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - dropdownWidth - 8));
    const spaceBelow = window.innerHeight - rect.bottom;
    const top = spaceBelow > estimatedHeight + 8 ? rect.bottom + 8 : rect.top - estimatedHeight - 8;
    setAnchorPos({ top, left });
  }, [anchorRef, estimatedHeight]);

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
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [open, onClose]);

  const openHeight = Math.max(34, Math.ceil(contentBounds.height) + 16);

  const positionStyle: React.CSSProperties = anchorPos
    ? { position: "fixed", top: anchorPos.top, left: anchorPos.left, zIndex: 9999 }
    : { position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, -50%)", zIndex: 9999 };

  return (
    <div
      ref={containerRef}
      className="anim-dropdown-container"
      style={positionStyle}
    >
      <motion.div
        initial={false}
        animate={{
          width: open ? 180 : 0,
          height: open ? openHeight : 0,
          opacity: open ? 1 : 0,
          borderRadius: 12,
        }}
        transition={{
          type: "spring",
          damping: 34,
          stiffness: 380,
          mass: 0.8,
        }}
        className="anim-dropdown-body"
        style={{ overflow: "hidden" }}
      >
        <div ref={contentRef} style={{ padding: "8px" }}>
          <motion.div
            initial={false}
            animate={{ opacity: open ? 1 : 0 }}
            transition={{ duration: 0.2, delay: open ? 0.08 : 0 }}
            style={{ pointerEvents: open ? "auto" : "none" }}
          >
            <div
              style={{
                fontSize: "0.75rem",
                fontWeight: 600,
                color: "var(--textDim)",
                padding: "4px 8px 8px",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Export as
            </div>
            <ul className="anim-dropdown-list">
              {exportFormats.map((item, index) => {
                const isLoading = loading === item.id;
                const showIndicator = hoveredItem === item.id;
                const itemDelay = open ? 0.06 + index * 0.02 : 0;

                return (
                  <motion.li
                    key={item.id}
                    initial={{ opacity: 0, x: 8 }}
                    animate={{
                      opacity: open ? 1 : 0,
                      x: open ? 0 : 8,
                    }}
                    transition={{
                      delay: itemDelay,
                      duration: 0.15,
                      ease: easeOutQuint,
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (!isLoading) onSelect(item.id);
                    }}
                    onMouseEnter={() => setHoveredItem(item.id)}
                    onMouseLeave={() => setHoveredItem(null)}
                    className={`anim-dropdown-item${isLoading ? " active" : ""}`}
                    style={{ opacity: isLoading ? 0.6 : 1, cursor: isLoading ? "wait" : "pointer" }}
                  >
                    {showIndicator && !isLoading && (
                      <motion.div
                        layoutId="exportIndicator"
                        className="anim-item-bg"
                        transition={{
                          type: "spring",
                          damping: 30,
                          stiffness: 520,
                          mass: 0.8,
                        }}
                      />
                    )}
                    {showIndicator && !isLoading && (
                      <motion.div
                        layoutId="exportLeftBar"
                        className="anim-item-bar"
                        transition={{
                          type: "spring",
                          damping: 30,
                          stiffness: 520,
                          mass: 0.8,
                        }}
                      />
                    )}
                    <span className="anim-item-label" style={{ paddingLeft: "6px" }}>
                      {isLoading ? `${item.label}...` : item.label}
                    </span>
                  </motion.li>
                );
              })}
            </ul>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
