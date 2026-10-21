import { Label } from "radix-ui";
import { type ComponentProps, useId } from "react";
import { cn } from "../../lib/utils";

type FieldProps = ComponentProps<"input"> & { label: string; error?: string };

export const fieldClassName =
  "h-11 w-full rounded-field border border-field-border bg-surface px-3.5 text-ink placeholder:text-meta aria-invalid:border-error-fg";

export function Field({ label, error, id, className, ...props }: FieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const errorId = `${inputId}-error`;
  return (
    <div className="flex flex-col gap-1.5">
      <Label.Root htmlFor={inputId} className="text-xs font-semibold text-ink-soft">
        {label}
      </Label.Root>
      <input
        id={inputId}
        className={cn(fieldClassName, className)}
        aria-invalid={error === undefined ? undefined : true}
        aria-describedby={error === undefined ? undefined : errorId}
        {...props}
      />
      {error !== undefined && (
        <p id={errorId} className="text-caption text-error-fg">
          {error}
        </p>
      )}
    </div>
  );
}
