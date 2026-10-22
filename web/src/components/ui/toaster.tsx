import { X } from "lucide-react";
import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";
import { IconButton } from "./button";
import { Notice } from "./notice";

export type Toast = { tone: "success" | "error"; message: string; detail?: string };

type ShownToast = Toast & { id: number };

const SUCCESS_DURATION = 5_000;

const ToastContext = createContext<{ show: (toast: Toast) => void } | undefined>(undefined);

let nextId = 0;

/**
 * Transient notices at the bottom of the screen, which outlive a navigation. A success hides by
 * itself; an error stays until it is closed, so it can be read.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ShownToast[]>([]);

  const close = useCallback(
    (id: number) => setToasts((shown) => shown.filter((toast) => toast.id !== id)),
    [],
  );
  const show = useCallback(
    (toast: Toast) => {
      nextId += 1;
      const id = nextId;
      setToasts((shown) => [...shown, { ...toast, id }]);
      if (toast.tone === "success") {
        setTimeout(() => close(id), SUCCESS_DURATION);
      }
    },
    [close],
  );
  const value = useMemo(() => ({ show }), [show]);

  return (
    <ToastContext value={value}>
      {children}
      <section
        aria-label="Avisos"
        className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 p-4"
      >
        {toasts.map((toast) => (
          <Notice
            key={toast.id}
            tone={toast.tone}
            className="pointer-events-auto flex w-full max-w-md items-start justify-between gap-3 bg-surface shadow-xl"
          >
            <div className="py-1">
              <p className="font-semibold">{toast.message}</p>
              {toast.detail !== undefined && <p className="mt-1 text-caption">{toast.detail}</p>}
            </div>
            <IconButton
              label="Cerrar aviso"
              className="-my-2 -mr-2"
              onClick={() => close(toast.id)}
            >
              <X aria-hidden="true" />
            </IconButton>
          </Notice>
        ))}
      </section>
    </ToastContext>
  );
}

export function useToast() {
  const toasts = useContext(ToastContext);
  if (toasts === undefined) {
    throw new Error("useToast needs a ToastProvider");
  }
  return toasts;
}
