import { RefreshCw } from "lucide-react";
import { useScrapeFeeds } from "../../api/feeds";
import { Button } from "../../components/ui/button";
import { useToast } from "../../components/ui/toaster";
import { isSessionEnd } from "./is-session-end";

/** Read the newspapers' front pages now; a run in progress is waited for like any other. */
export function ScrapeButton() {
  const scrape = useScrapeFeeds();
  const { show } = useToast();

  const run = () =>
    scrape.mutate(undefined, {
      onSuccess: (stored) => show({ tone: "success", message: describeRun(stored.length) }),
      onError: (error) => {
        if (!isSessionEnd(error)) {
          show({
            tone: "error",
            message: "No se pudieron actualizar las portadas",
            detail: error.message,
          });
        }
      },
    });

  return (
    <Button variant="secondary" disabled={scrape.isPending} onClick={run}>
      <RefreshCw aria-hidden="true" />
      {scrape.isPending ? "Actualizando…" : "Actualizar portadas"}
    </Button>
  );
}

function describeRun(count: number): string {
  if (count === 0) {
    return "No hay noticias nuevas";
  }
  return `Portadas actualizadas: ${count} ${count === 1 ? "noticia nueva" : "noticias nuevas"}`;
}
