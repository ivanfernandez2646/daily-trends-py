import type { ReactNode } from "react";

type EmptyStateProps = { message: string; action?: ReactNode };

export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-start gap-4 py-10">
      <p className="font-serif text-title-2 text-ink">{message}</p>
      {action}
    </div>
  );
}
