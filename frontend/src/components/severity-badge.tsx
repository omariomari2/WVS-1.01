import { cn } from "@/lib/utils";
import { SEVERITY_COLORS } from "@/lib/types";

interface SeverityBadgeProps {
  severity: string;
  className?: string;
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide",
        SEVERITY_COLORS[severity] || "bg-gray-500 text-white",
        className
      )}
    >
      {severity}
    </span>
  );
}
