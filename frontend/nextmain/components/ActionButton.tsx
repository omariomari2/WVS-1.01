"use client";

interface ActionButtonProps {
  label: string;
  variant: "first" | "sec" | "third" | "fourth" | "upload" | "scrape";
  visible?: boolean;
  onClick?: () => void;
  disabled?: boolean;
}

export default function ActionButton({
  label,
  variant,
  visible,
  onClick,
  disabled,
}: ActionButtonProps) {
  const visibilityClass =
    variant === "upload" || variant === "scrape"
      ? ""
      : visible
        ? "button-visible"
        : "";

  const wrapperClass =
    variant === "scrape"
      ? `button scrape-btn ${visibilityClass}`.trim()
      : `button ${variant} ${visibilityClass}`.trim();

  return (
    <div className={wrapperClass}>
      <button
        type="button"
        className="action-btn"
        disabled={disabled}
        style={disabled ? { opacity: 0.6 } : undefined}
        onClick={() => {
          if (!disabled && onClick) onClick();
        }}
      >
        {label}
      </button>
      <span className="btn-glow" />
    </div>
  );
}
