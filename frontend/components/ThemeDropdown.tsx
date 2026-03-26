"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import useMeasure from "react-use-measure";
import { HugeiconsIcon } from "@hugeicons/react";
import { ArrowDown01Icon } from "@hugeicons/core-free-icons";
import { FINDING_FILTER_OPTIONS, type FindingFilter } from "@/lib/types";

const easeOutQuint: [number, number, number, number] = [0.23, 1, 0.32, 1];

interface ThemeDropdownProps {
  value: FindingFilter;
  onChange: (value: FindingFilter) => void;
}

export default function ThemeDropdown({ value, onChange }: ThemeDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [contentRef, contentBounds] = useMeasure();
  const activeLabel =
    FINDING_FILTER_OPTIONS.find((item) => item.id === value)?.label || "All";
  const closedWidth = Math.max(96, activeLabel.length * 8 + 34);
  const openWidth = 164;

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const openHeight = Math.max(34, Math.ceil(contentBounds.height) + 16);

  return (
    <div ref={containerRef} className="anim-dropdown-container">
      <motion.div
        layout
        initial={false}
        animate={{
          width: isOpen ? openWidth : closedWidth,
          height: isOpen ? openHeight : 34,
          borderRadius: isOpen ? 12 : 10,
        }}
        transition={{
          type: "spring",
          damping: 34,
          stiffness: 380,
          mass: 0.8,
        }}
        className="anim-dropdown-body"
        onClick={() => !isOpen && setIsOpen(true)}
      >
        <motion.div
          initial={false}
          animate={{
            opacity: isOpen ? 0 : 1,
            scale: isOpen ? 0.95 : 1,
          }}
          transition={{ duration: 0.15 }}
          className="anim-dropdown-closed-icon"
          style={{
            pointerEvents: isOpen ? "none" : "auto",
            willChange: "transform",
          }}
        >
          <span className="anim-dropdown-closed-label">{activeLabel}</span>
          <motion.span
            initial={false}
            animate={{ rotate: isOpen ? 180 : 0 }}
            transition={{ duration: 0.18 }}
            className="anim-dropdown-chevron"
            aria-hidden="true"
          >
            <HugeiconsIcon icon={ArrowDown01Icon} size={14} strokeWidth={1.8} />
          </motion.span>
        </motion.div>

        <div ref={contentRef} style={{ padding: "8px" }}>
          <motion.div
            layout
            initial={false}
            animate={{ opacity: isOpen ? 1 : 0 }}
            transition={{ duration: 0.2, delay: isOpen ? 0.08 : 0 }}
            style={{
              pointerEvents: isOpen ? "auto" : "none",
              willChange: "transform",
            }}
          >
            <ul className="anim-dropdown-list">
              {FINDING_FILTER_OPTIONS.map((item, index) => {
                const isActive = value === item.id;
                const showIndicator = hoveredItem
                  ? hoveredItem === item.id
                  : isActive;
                const itemDelay = isOpen ? 0.06 + index * 0.02 : 0;

                return (
                  <motion.li
                    key={item.id}
                    initial={{ opacity: 0, x: 8 }}
                    animate={{
                      opacity: isOpen ? 1 : 0,
                      x: isOpen ? 0 : 8,
                    }}
                    transition={{
                      delay: itemDelay,
                      duration: 0.15,
                      ease: easeOutQuint,
                    }}
                    onClick={(event) => {
                      event.stopPropagation();
                      onChange(item.id);
                      setIsOpen(false);
                    }}
                    onMouseEnter={() => setHoveredItem(item.id)}
                    onMouseLeave={() => setHoveredItem(null)}
                    className={`anim-dropdown-item ${isActive ? "active" : ""}`}
                  >
                    {showIndicator && (
                      <motion.div
                        layoutId="activeIndicator"
                        className="anim-item-bg"
                        transition={{
                          type: "spring",
                          damping: 30,
                          stiffness: 520,
                          mass: 0.8,
                        }}
                      />
                    )}
                    {showIndicator && (
                      <motion.div
                        layoutId="leftBar"
                        className="anim-item-bar"
                        transition={{
                          type: "spring",
                          damping: 30,
                          stiffness: 520,
                          mass: 0.8,
                        }}
                      />
                    )}
                    <span
                      className="anim-item-label"
                      style={{ paddingLeft: "6px" }}
                    >
                      {item.label}
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
