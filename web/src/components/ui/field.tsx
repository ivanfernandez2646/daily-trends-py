import { Label } from "radix-ui";
import { type ComponentProps, type ReactNode, useId } from "react";
import { cn } from "../../lib/utils";

type LabelledProps = { label: string; error?: string };

export const fieldClassName =
  "h-11 w-full rounded-field border border-field-border bg-surface px-3.5 text-ink placeholder:text-meta aria-invalid:border-error-fg";

export function Field({
  label,
  error,
  id,
  className,
  ...props
}: ComponentProps<"input"> & LabelledProps) {
  return (
    <Labelled label={label} error={error} id={id}>
      {(control) => <input className={cn(fieldClassName, className)} {...control} {...props} />}
    </Labelled>
  );
}

export function TextareaField({
  label,
  error,
  id,
  className,
  ...props
}: ComponentProps<"textarea"> & LabelledProps) {
  return (
    <Labelled label={label} error={error} id={id}>
      {(control) => (
        <textarea
          className={cn(fieldClassName, "h-auto min-h-28 py-2.5 leading-normal", className)}
          {...control}
          {...props}
        />
      )}
    </Labelled>
  );
}

type ControlProps = {
  id: string;
  "aria-invalid"?: true;
  "aria-describedby"?: string;
};

/** A label above its control and an error below, linked to it. */
function Labelled({
  label,
  error,
  id,
  children,
}: LabelledProps & { id?: string; children: (control: ControlProps) => ReactNode }) {
  const generatedId = useId();
  const controlId = id ?? generatedId;
  const errorId = `${controlId}-error`;
  return (
    <div className="flex flex-col gap-1.5">
      <Label.Root htmlFor={controlId} className="text-xs font-semibold text-ink-soft">
        {label}
      </Label.Root>
      {children({
        id: controlId,
        ...(error !== undefined && { "aria-invalid": true, "aria-describedby": errorId }),
      })}
      {error !== undefined && (
        <p id={errorId} className="text-caption text-error-fg">
          {error}
        </p>
      )}
    </div>
  );
}
