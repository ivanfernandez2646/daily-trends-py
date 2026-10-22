import { createFileRoute, redirect } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { useState } from "react";
import { useFeedList } from "../api/feeds";
import type { FeedFilters, FeedResponse } from "../api/types";
import { Button } from "../components/ui/button";
import { EmptyState } from "../components/ui/empty-state";
import { DeleteFeedDialog } from "../features/admin/delete-feed-dialog";
import { FeedsTable, FeedsTableSkeleton } from "../features/admin/feeds-table";
import { ScrapeButton } from "../features/admin/scrape-button";
import { CategoryChips } from "../features/feeds/category-chips";
import {
  countFilters,
  describeFilters,
  filtersToRewrite,
  parseFeedFilters,
  updateFilters,
} from "../features/feeds/feed-filters";
import { LoadError } from "../features/feeds/load-error";
import { SearchBox } from "../features/feeds/search-box";
import { SourceSelect } from "../features/feeds/source-select";

export const Route = createFileRoute("/admin/")({
  validateSearch: parseFeedFilters,
  beforeLoad: ({ location }) => {
    const rewrite = filtersToRewrite(location.search);
    if (rewrite !== undefined) {
      throw redirect({ to: "/admin", search: rewrite, replace: true });
    }
  },
  component: FeedsAdminPage,
});

function FeedsAdminPage() {
  const filters = Route.useSearch();
  const navigate = Route.useNavigate();
  const list = useFeedList(filters);
  const [deleting, setDeleting] = useState<FeedResponse>();

  const change = (update: Partial<FeedFilters>) =>
    void navigate({ search: (current) => updateFilters(current, update) });
  const clear = () => void navigate({ search: {} });

  const active = countFilters(filters);
  const description = describeFilters(filters);
  const feeds = list.data?.pages.flatMap((page) => page.items);

  return (
    <div className="mx-auto flex max-w-content flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-serif text-title-1">Noticias</h1>
        <div className="flex flex-wrap gap-3">
          <ScrapeButton />
          <Button disabled>
            <Plus aria-hidden="true" />
            Nueva noticia
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-4 rounded-card border border-rule bg-surface p-4">
        <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_12.5rem]">
          <SearchBox q={filters.q} onSearch={(q) => change({ q })} />
          <SourceSelect source={filters.source} onChange={(source) => change({ source })} />
        </div>
        <CategoryChips category={filters.category} onChange={(category) => change({ category })} />
      </div>

      {active > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-4 text-caption text-meta">
          <p>Noticias {description}</p>
          <Button variant="link" onClick={clear}>
            Limpiar filtros
          </Button>
        </div>
      )}

      {feeds !== undefined ? (
        feeds.length === 0 ? (
          <EmptyState
            message={active === 0 ? "Todavía no hay noticias." : `No hay noticias ${description}.`}
            action={
              active > 0 && (
                <Button variant="secondary" onClick={clear}>
                  Limpiar filtros
                </Button>
              )
            }
          />
        ) : (
          <FeedsTable
            feeds={feeds}
            hasMore={list.hasNextPage}
            loadingMore={list.isFetchingNextPage}
            onLoadMore={() => void list.fetchNextPage()}
            onDelete={setDeleting}
          />
        )
      ) : list.isError ? (
        <LoadError onRetry={() => void list.refetch()} />
      ) : (
        <FeedsTableSkeleton />
      )}
      {list.isFetchNextPageError && <LoadError onRetry={() => void list.fetchNextPage()} />}

      <DeleteFeedDialog feed={deleting} onClose={() => setDeleting(undefined)} />
    </div>
  );
}
