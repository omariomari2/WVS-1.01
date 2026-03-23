import { cn } from "@/lib/utils";
import { HTMLAttributes } from "react";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "outline";
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
        {
          "bg-[var(--card-border)] text-[var(--foreground)]": variant === "default",
          "border border-[var(--card-border)]": variant === "outline",
        },
        className
      )}
      {...props}
    />
  );
}
