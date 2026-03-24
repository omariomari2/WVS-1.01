"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "motion/react";
import useMeasure from "react-use-measure";

const menuItems = [
    { id: "critical", label: "Critical" },
    { id: "medium", label: "Medium" },
    { id: "low", label: "Low" },
];

const easeOutQuint: [number, number, number, number] = [0.23, 1, 0.32, 1];

export default function ThemeDropdown() {
    const [isOpen, setIsOpen] = useState(false);
    const [activeItem, setActiveItem] = useState("critical");
    const [hoveredItem, setHoveredItem] = useState<string | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const [contentRef, contentBounds] = useMeasure();
    const activeLabel = menuItems.find(m => m.id === activeItem)?.label;

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
                    width: isOpen ? 120 : 96,
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
                {/* Closed State Text */}
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
                        justifyContent: "space-between",
                        padding: "0 12px",
                    }}
                >
                    <span style={{ fontSize: "0.8rem", fontWeight: 500, color: "var(--textDim)" }}>{activeLabel}</span>
                    <span style={{ fontSize: "0.5rem", color: "var(--textDim)" }}>▼</span>
                </motion.div>

                {/* Menu Content */}
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
                            {menuItems.map((item, index) => {
                                const isActive = activeItem === item.id;
                                const showIndicator = hoveredItem ? hoveredItem === item.id : isActive;
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
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            setActiveItem(item.id);
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
                                        <span className="anim-item-label" style={{ paddingLeft: "6px" }}>{item.label}</span>
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
