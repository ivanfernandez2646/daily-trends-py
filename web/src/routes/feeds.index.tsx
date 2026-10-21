import { createFileRoute } from "@tanstack/react-router";
import { parseFeedFilters } from "../features/feeds/feed-filters";
import { ReaderPage } from "../features/feeds/reader-page";

// The browse page: its list and filters come with the browse screen (S14, phase 4).
export const Route = createFileRoute("/feeds/")({
  validateSearch: parseFeedFilters,
  component: BrowsePage,
});

function BrowsePage() {
  return (
    <ReaderPage variant="compact">
      <main className="py-12">
        <h1 className="font-serif text-title-1">Explorar</h1>
      </main>
    </ReaderPage>
  );
}
