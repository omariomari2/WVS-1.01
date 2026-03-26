"use client";

import { useLayoutEffect, useRef } from "react";
import gsap from "gsap";

export default function HeroTitle() {
  const containerRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (!containerRef.current) return;
    const ctx = gsap.context(() => {
      const children = containerRef.current?.querySelectorAll("p");
      if (!children) return;
      gsap.from(children, {
        y: 90,
        opacity: 0,
        duration: 1.2,
        stagger: 0.12,
        ease: "power4.out",
        clearProps: "all",
      });
    }, containerRef);
    return () => ctx.revert();
  }, []);

  return (
    <div className="title" ref={containerRef}>
      <p>Web</p>
      <p>Vunerability</p>
      <p>Scan</p>
    </div>
  );
}
