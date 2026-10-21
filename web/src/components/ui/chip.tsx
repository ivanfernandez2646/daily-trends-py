import { Toggle } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "../../lib/utils";

export function Chip({ className, ...props }: ComponentProps<typeof Toggle.Root>) {
  return (
    <Toggle.Root
      data-slot="chip"
      className={cn(
        "inline-flex h-10 items-center gap-2 rounded-full border border-field-border bg-surface px-4 text-sm font-medium text-ink transition-colors duration-150 ease-out hover:border-ink data-[state=on]:border-ink data-[state=on]:bg-ink data-[state=on]:text-surface",
        className,
      )}
      {...props}
    />
  );
}
