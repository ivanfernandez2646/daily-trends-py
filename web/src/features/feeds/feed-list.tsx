import type { FeedResponse } from "../../api/types";
import { Button } from "../../components/ui/button";
import { Skeleton } from "../../components/ui/skeleton";
import { FeedCard } from "./feed-card";

type FeedListProps = {
  feeds: FeedResponse[];
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
};

export function FeedList({ feeds, hasMore, loadingMore, onLoadMore }: FeedListProps) {
  return (
    <>
      <ol aria-label="Noticias">
        {feeds.map((feed) => (
          <li key={feed.id}>
            <FeedCard feed={feed} variant="row" />
          </li>
        ))}
      </ol>
      {hasMore && (
        <div className="flex justify-center border-t border-rule pt-8">
          <Button onClick={onLoadMore} disabled={loadingMore} className="h-12 px-7">
            {loadingMore ? "Cargando…" : "Cargar más"}
          </Button>
        </div>
      )}
    </>
  );
}

export function FeedListSkeleton() {
  return (
    <div role="status">
      <span className="sr-only">Cargando noticias</span>
      {[0, 1, 2, 3].map((index) => (
        <div
          key={index}
          className="grid grid-cols-[5rem_minmax(0,1fr)] gap-4 border-t border-rule py-6 sm:grid-cols-[7.5rem_minmax(0,1fr)] sm:gap-8"
        >
          <Skeleton className="h-4 w-12" />
          <div className="flex flex-col gap-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}
