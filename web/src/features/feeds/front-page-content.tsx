import { Link } from "@tanstack/react-router";
import type { FeedResponse } from "../../api/types";
import { EmptyState } from "../../components/ui/empty-state";
import { Skeleton } from "../../components/ui/skeleton";
import { FeedCard } from "./feed-card";
import { splitFrontPage } from "./front-page";

export function FrontPageContent({ feeds }: { feeds: FeedResponse[] }) {
  const { lead, side, more } = splitFrontPage(feeds);
  if (lead === undefined) {
    return (
      <EmptyState message="Aún no hay noticias. La portada se llenará cuando se lean los periódicos." />
    );
  }
  return (
    <>
      <section aria-label="Destacadas" className="flex flex-wrap gap-10 border-b border-rule py-10">
        <div className="min-w-0 flex-[7_1_32rem]">
          <FeedCard feed={lead} variant="lead" />
        </div>
        {side.length > 0 && (
          <div className="flex min-w-0 flex-[5_1_20rem] flex-col md:border-l md:border-rule md:pl-10">
            {side.map((feed) => (
              <FeedCard key={feed.id} feed={feed} variant="side" />
            ))}
          </div>
        )}
      </section>
      {more.length > 0 && (
        <section aria-labelledby="more-headlines" className="py-10">
          <div className="mb-6 flex flex-wrap items-baseline justify-between gap-4">
            <h2 id="more-headlines" className="font-serif text-[28px] font-medium">
              Más titulares
            </h2>
            <Link to="/feeds" className="text-sm font-semibold text-accent hover:underline">
              Ver todas las noticias →
            </Link>
          </div>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(min(100%,18.75rem),1fr))] gap-x-10">
            {more.map((feed) => (
              <FeedCard key={feed.id} feed={feed} variant="grid" />
            ))}
          </div>
        </section>
      )}
    </>
  );
}

export function FrontPageSkeleton() {
  return (
    <div role="status" className="flex flex-wrap gap-10 border-b border-rule py-10">
      <span className="sr-only">Cargando noticias</span>
      <div className="flex min-w-0 flex-[7_1_32rem] flex-col gap-4">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-12 w-11/12" />
        <Skeleton className="h-12 w-3/4" />
        <Skeleton className="h-5 w-2/3" />
      </div>
      <div className="flex min-w-0 flex-[5_1_20rem] flex-col gap-8">
        {[0, 1, 2].map((index) => (
          <div key={index} className="flex flex-col gap-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-3 w-32" />
          </div>
        ))}
      </div>
    </div>
  );
}
