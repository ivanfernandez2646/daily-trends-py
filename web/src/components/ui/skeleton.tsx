import { cn } from "../../lib/utils";

/** A placeholder bar shaped like the content it stands for. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn("rounded bg-rule motion-safe:animate-pulse", className)}
    />
  );
}
