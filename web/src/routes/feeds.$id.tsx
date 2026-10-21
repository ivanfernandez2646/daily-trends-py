import { createFileRoute, Link } from "@tanstack/react-router";
import { ApiError } from "../api/client";
import { useFeed, useRelatedFeeds } from "../api/feeds";
import { FeedDetail, FeedDetailSkeleton } from "../features/feeds/feed-detail";
import { LoadError } from "../features/feeds/load-error";
import { NotFoundPage } from "../features/feeds/not-found-page";
import { ReaderPage } from "../features/feeds/reader-page";
import { RelatedFeeds } from "../features/feeds/related-feeds";

export const Route = createFileRoute("/feeds/$id")({ component: FeedPage });

function FeedPage() {
  const { id } = Route.useParams();
  const { data: feed, error, refetch } = useFeed(id);
  const { data: related = [] } = useRelatedFeeds(feed?.category, id);

  // An id that is not a UUID (400) names no feed either.
  if (error instanceof ApiError && (error.status === 404 || error.status === 400)) {
    return <NotFoundPage subject="noticia" />;
  }

  return (
    <ReaderPage variant="compact">
      <main className="mx-auto max-w-reading pt-14 pb-20">
        <Link
          to="/feeds"
          className="inline-flex min-h-11 items-center text-sm font-medium text-meta hover:text-accent"
        >
          ← Volver a Explorar
        </Link>
        <div className="mt-4">
          {feed !== undefined ? (
            <>
              <FeedDetail feed={feed} />
              {related.length > 0 && <RelatedFeeds category={feed.category} feeds={related} />}
            </>
          ) : error !== null ? (
            <LoadError onRetry={() => void refetch()} />
          ) : (
            <FeedDetailSkeleton />
          )}
        </div>
      </main>
    </ReaderPage>
  );
}
