import { createFileRoute } from "@tanstack/react-router";
import { useHomeFeeds } from "../api/feeds";
import { lastUpdated } from "../features/feeds/front-page";
import { FrontPageContent, FrontPageSkeleton } from "../features/feeds/front-page-content";
import { LoadError } from "../features/feeds/load-error";
import { ReaderPage } from "../features/feeds/reader-page";

export const Route = createFileRoute("/")({ component: FrontPage });

function FrontPage() {
  const { data: feeds, isError, refetch } = useHomeFeeds();
  return (
    <ReaderPage variant="front" updatedAt={feeds && lastUpdated(feeds)}>
      <main>
        {feeds !== undefined ? (
          <FrontPageContent feeds={feeds} />
        ) : isError ? (
          <LoadError onRetry={() => void refetch()} />
        ) : (
          <FrontPageSkeleton />
        )}
      </main>
    </ReaderPage>
  );
}
