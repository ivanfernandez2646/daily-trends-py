import type { ReactNode } from "react";
import { ReaderFooter } from "./reader-footer";
import { ReaderHeader } from "./reader-header";

type ReaderPageProps = { children: ReactNode } & (
  | { variant: "front"; updatedAt?: string }
  | { variant: "compact" }
);

/** A page of the reader: its header, the page's own `main`, and the footer. */
export function ReaderPage({ children, ...header }: ReaderPageProps) {
  return (
    <div className="mx-auto max-w-content px-4 sm:px-8">
      {header.variant === "front" ? (
        <ReaderHeader variant="front" updatedAt={header.updatedAt} />
      ) : (
        <ReaderHeader variant="compact" />
      )}
      {children}
      <ReaderFooter />
    </div>
  );
}
