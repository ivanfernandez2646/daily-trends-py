import { AlertDialog } from "radix-ui";
import { type ReactNode, useRef } from "react";
import { Button } from "./button";

type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel: string;
  /** What the confirm button says while `pending`, such as *Borrando…*. */
  pendingLabel?: string;
  pending?: boolean;
  destructive?: boolean;
  onConfirm: () => void;
  /** What the question is about, and any error of the confirmed action. */
  children?: ReactNode;
};

/** A question before an action that cannot be undone: focus stays inside, Escape cancels. */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  pendingLabel = confirmLabel,
  pending = false,
  destructive = true,
  onConfirm,
  children,
}: ConfirmDialogProps) {
  // Opened from any button, not a Radix trigger: focus goes back to whatever opened it.
  const opener = useRef<HTMLElement | null>(null);
  return (
    <AlertDialog.Root open={open} onOpenChange={onOpenChange}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-40 bg-ink/40" />
        <AlertDialog.Content
          onOpenAutoFocus={() => {
            opener.current =
              document.activeElement instanceof HTMLElement ? document.activeElement : null;
          }}
          onCloseAutoFocus={(event) => {
            if (opener.current?.isConnected) {
              event.preventDefault();
              opener.current.focus();
            }
          }}
          className="fixed top-1/2 left-1/2 z-50 flex w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 flex-col gap-4 rounded-dialog border border-rule bg-surface p-6 text-ink shadow-xl"
        >
          <AlertDialog.Title className="font-serif text-title-2">{title}</AlertDialog.Title>
          <AlertDialog.Description className="text-ink-soft">{description}</AlertDialog.Description>
          {children}
          <div className="mt-2 flex flex-wrap justify-end gap-3">
            <AlertDialog.Cancel asChild>
              <Button variant="secondary">Cancelar</Button>
            </AlertDialog.Cancel>
            {/* Not an AlertDialog.Action: the dialog stays open until the action has finished. */}
            <Button
              variant={destructive ? "destructive" : "primary"}
              disabled={pending}
              onClick={onConfirm}
            >
              {pending ? pendingLabel : confirmLabel}
            </Button>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
