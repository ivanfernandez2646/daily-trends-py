import { createFileRoute, redirect, useLocation } from "@tanstack/react-router";
import { SlidersHorizontal } from "lucide-react";
import { useId, useState } from "react";
import { useFeedList } from "../api/feeds";
import type { FeedFilters } from "../api/types";
import { Button } from "../components/ui/button";
import { EmptyState } from "../components/ui/empty-state";
import { CategoryChips } from "../features/feeds/category-chips";
import {
  countFilters,
  describeFilters,
  filtersToRewrite,
  parseFeedFilters,
  updateFilters,
} from "../features/feeds/feed-filters";
import { FeedList, FeedListSkeleton } from "../features/feeds/feed-list";
import { LoadError } from "../features/feeds/load-error";
import { ReaderPage } from "../features/feeds/reader-page";
import { SearchBox } from "../features/feeds/search-box";
import { SourceSelect } from "../features/feeds/source-select";
import { cn } from "../lib/utils";

export const Route = createFileRoute("/feeds/")({
  validateSearch: parseFeedFilters,
  // A link with an invalid filter is rewritten to the URL the page really uses. The raw
  // `location.search` is checked: the route's `search` also keeps the root's unvalidated params.
  beforeLoad: ({ location }) => {
    const rewrite = filtersToRewrite(location.search);
    if (rewrite !== undefined) {
      throw redirect({ to: "/feeds", search: rewrite, replace: true });
    }
  },
  component: BrowsePage,
});

function BrowsePage() {
  const filters = Route.useSearch();
  const navigate = Route.useNavigate();
  const comingToSearch = useLocation({ select: (location) => location.hash === "buscar" });
  const [filtersOpen, setFiltersOpen] = useState(false);
  const filtersId = useId();
  const list = useFeedList(filters);

  const change = (update: Partial<FeedFilters>) =>
    void navigate({ search: (current) => updateFilters(current, update) });
  const clear = () => void navigate({ search: {} });

  const active = countFilters(filters);
  const description = describeFilters(filters);
  const feeds = list.data?.pages.flatMap((page) => page.items);

  return (
    <ReaderPage variant="compact">
      <main className="pt-12 pb-16">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="font-serif text-title-1">Explorar</h1>
            <p className="mt-2 text-meta">
              Todas las noticias, de la más reciente a la más antigua.
            </p>
          </div>
          <Button
            variant="secondary"
            className="sm:hidden"
            aria-expanded={filtersOpen}
            aria-controls={filtersId}
            aria-label={
              active === 0
                ? "Filtros"
                : `Filtros (${active} ${active === 1 ? "activo" : "activos"})`
            }
            onClick={() => setFiltersOpen((open) => !open)}
          >
            <SlidersHorizontal aria-hidden="true" />
            Filtros
            {active > 0 && (
              <span className="grid size-5 place-items-center rounded-full bg-ink text-xs text-surface">
                {active}
              </span>
            )}
          </Button>
        </div>

        <div
          id={filtersId}
          className={cn(
            "flex-col gap-6 border-b border-rule pb-6 sm:flex",
            filtersOpen ? "flex" : "hidden",
          )}
        >
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_12.5rem]">
            <SearchBox q={filters.q} focused={comingToSearch} onSearch={(q) => change({ q })} />
            <SourceSelect source={filters.source} onChange={(source) => change({ source })} />
          </div>
          <CategoryChips
            category={filters.category}
            onChange={(category) => change({ category })}
          />
        </div>

        {active > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-4 py-2 text-caption text-meta">
            <p>Noticias {description}</p>
            <Button variant="link" onClick={clear}>
              Limpiar filtros
            </Button>
          </div>
        )}

        <div className="mt-4">
          {feeds !== undefined ? (
            feeds.length === 0 ? (
              <EmptyState
                message={
                  active === 0 ? "Todavía no hay noticias." : `No hay noticias ${description}.`
                }
                action={
                  active > 0 && (
                    <Button variant="secondary" onClick={clear}>
                      Limpiar filtros
                    </Button>
                  )
                }
              />
            ) : (
              <FeedList
                feeds={feeds}
                hasMore={list.hasNextPage}
                loadingMore={list.isFetchingNextPage}
                onLoadMore={() => void list.fetchNextPage()}
              />
            )
          ) : list.isError ? (
            <LoadError onRetry={() => void list.refetch()} />
          ) : (
            <FeedListSkeleton />
          )}
          {list.isFetchNextPageError && <LoadError onRetry={() => void list.fetchNextPage()} />}
        </div>
      </main>
    </ReaderPage>
  );
}
