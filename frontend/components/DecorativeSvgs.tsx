"use client";

import { useLayoutEffect, useRef } from "react";
import gsap from "gsap";

export default function DecorativeSvgs() {
  const topRef = useRef<SVGSVGElement>(null);
  const bottomRef = useRef<SVGSVGElement>(null);

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      if (topRef.current) {
        gsap.from(topRef.current, {
          opacity: 0,
          duration: 1.4,
          clearProps: "opacity",
        });
        gsap.to(topRef.current, {
          y: -14,
          rotation: 4,
          duration: 5,
          ease: "sine.inOut",
          yoyo: true,
          repeat: -1,
        });
      }
      if (bottomRef.current) {
        gsap.from(bottomRef.current, {
          opacity: 0,
          duration: 1.4,
          clearProps: "opacity",
        });
        gsap.to(bottomRef.current, {
          y: 12,
          rotation: -3,
          duration: 6.5,
          ease: "sine.inOut",
          yoyo: true,
          repeat: -1,
          delay: 1.5,
        });
      }
    });
    return () => ctx.revert();
  }, []);

  return (
    <>
      <svg
        ref={topRef}
        className="top-right"
        width="219"
        height="147"
        viewBox="0 0 219 147"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect
          opacity="0.18"
          x="10.4252"
          y="75.8326"
          width="7.50168"
          height="7.50168"
          transform="rotate(110.283 10.4252 75.8326)"
          fill="#686868"
          stroke="white"
          strokeWidth="1.22683"
        />
        <rect
          opacity="0.18"
          x="180.869"
          y="138.825"
          width="7.50168"
          height="7.50168"
          transform="rotate(110.283 180.869 138.825)"
          fill="#686868"
          stroke="white"
          strokeWidth="1.22683"
        />
        <rect
          x="69.4713"
          y="-91.84"
          width="180.485"
          height="180.485"
          transform="rotate(20.2832 69.4713 -91.84)"
          stroke="white"
          strokeOpacity="0.1"
          strokeWidth="1.22683"
        />
      </svg>

      <svg
        ref={bottomRef}
        className="bottom-left"
        width="232"
        height="191"
        viewBox="0 0 232 191"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle
          cx="50.5685"
          cy="172.432"
          r="112.068"
          stroke="white"
          strokeOpacity="0.09"
        />
        <g opacity="0.1">
          <path d="M26.4932 5.20547L228.856 172.432" stroke="#D9D9D9" />
          <rect
            x="22.4384"
            y="0.5"
            width="6.15753"
            height="6.15753"
            fill="#686868"
            stroke="white"
          />
          <rect
            x="224.801"
            y="169.027"
            width="6.15753"
            height="6.15753"
            fill="#686868"
            stroke="white"
          />
          <circle
            cx="121.819"
            cy="83.613"
            r="1.7774"
            fill="#323232"
            stroke="white"
          />
        </g>
      </svg>
    </>
  );
}
