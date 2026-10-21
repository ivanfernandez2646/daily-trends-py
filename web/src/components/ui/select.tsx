import { Label } from "radix-ui";
import { type ComponentProps, useId } from "react";
import { cn } from "../../lib/utils";
import { fieldClassName } from "./field";

type SelectProps = ComponentProps<"select"> & { label: string };

/** A native select: the best picker on phones and for assistive technology. */
export function Select({ label, id, className, children, ...props }: SelectProps) {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  return (
    <div className="flex flex-col gap-1.5">
      <Label.Root htmlFor={selectId} className="text-xs font-semibold text-ink-soft">
        {label}
      </Label.Root>
      <select id={selectId} className={cn(fieldClassName, "px-3", className)} {...props}>
        {children}
      </select>
    </div>
  );
}
