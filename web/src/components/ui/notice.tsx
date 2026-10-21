import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

type NoticeProps = { tone: "success" | "error"; children: ReactNode; className?: string };

export function Notice({ tone, children, className }: NoticeProps) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cn(
        "rounded-field border px-4 py-3",
        tone === "error"
          ? "border-error-fg/25 bg-error-bg text-error-fg"
          : "border-success-fg/25 bg-success-bg text-success-fg",
        className,
      )}
    >
      {children}
    </div>
  );
}
