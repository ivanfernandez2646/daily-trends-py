import { Link } from "@tanstack/react-router";
import { ReaderPage } from "./reader-page";

/** A feed or an address that does not exist. */
export function NotFoundPage({ subject }: { subject: "noticia" | "página" }) {
  return (
    <ReaderPage variant="compact">
      <main className="mx-auto flex max-w-reading flex-col items-start gap-6 py-20">
        <h1 className="font-serif text-title-1">No encontramos esta {subject}.</h1>
        <p className="text-ink-soft">Puede que se haya borrado o que el enlace no sea correcto.</p>
        <Link to="/" className="font-semibold text-accent hover:underline">
          Volver a la portada
        </Link>
      </main>
    </ReaderPage>
  );
}
