import { Button } from "../../components/ui/button";
import { Notice } from "../../components/ui/notice";

/** A read that failed: never an empty state, always a way to try again. */
export function LoadError({ onRetry }: { onRetry: () => void }) {
  return (
    <Notice tone="error" className="my-10 flex flex-wrap items-center justify-between gap-4">
      <p>No se han podido cargar las noticias. Comprueba tu conexión e inténtalo de nuevo.</p>
      <Button variant="secondary" onClick={onRetry}>
        Reintentar
      </Button>
    </Notice>
  );
}
