import { Link } from "@tanstack/react-router";
import type { FeedResponse } from "../../api/types";
import { CategoryLabel } from "../../components/ui/category-label";
import { Skeleton } from "../../components/ui/skeleton";
import { SourceLink } from "../../components/ui/source-link";
import { Time } from "../../components/ui/time";
import { sourceLabel } from "../../lib/labels";
import { shortenArticleUrl } from "../../lib/urls";

export function FeedDetail({ feed }: { feed: FeedResponse }) {
  return (
    <article className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link to="/feeds" search={{ category: feed.category }} className="hover:text-accent">
          <CategoryLabel category={feed.category} />
        </Link>
        <span aria-hidden="true" className="text-field-border">
          /
        </span>
        <span className="font-serif font-medium">{sourceLabel(feed.source)}</span>
      </div>

      <h1 className="font-serif text-display">{feed.title}</h1>

      {feed.description !== null && (
        <p className="font-serif text-lead text-ink-soft">{feed.description}</p>
      )}

      <dl className="mt-2 grid grid-cols-[repeat(auto-fit,minmax(10rem,1fr))] gap-x-8 gap-y-4 border-t border-ink border-b border-b-rule py-5 text-caption">
        <div>
          <dt className="text-meta">Autor</dt>
          <dd className="mt-0.5 font-medium">{feed.author}</dd>
        </div>
        <div>
          <dt className="text-meta">Publicada</dt>
          <dd className="mt-0.5 font-medium">
            <Time iso={feed.created_at} format="full" />
          </dd>
        </div>
        {feed.updated_at !== null && (
          <div>
            <dt className="text-meta">Editada</dt>
            <dd className="mt-0.5 font-medium">
              <Time iso={feed.updated_at} format="full" />
            </dd>
          </div>
        )}
      </dl>

      {feed.url !== null && <SourcePanel url={feed.url} source={feed.source} />}
    </article>
  );
}

function SourcePanel({ url, source }: { url: string; source: string }) {
  const { host, path } = shortenArticleUrl(url);
  return (
    <section
      aria-label="Fuente original"
      className="flex flex-wrap items-center justify-between gap-5 rounded-card border border-rule bg-surface p-6"
    >
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="text-caption text-meta">Noticia completa en su fuente original</span>
        <span className="text-sm font-medium [overflow-wrap:anywhere]">
          {host}
          {path}
        </span>
      </div>
      <SourceLink url={url} source={source} variant="button" />
    </section>
  );
}

export function FeedDetailSkeleton() {
  return (
    <div role="status" className="flex flex-col gap-6">
      <span className="sr-only">Cargando la noticia</span>
      <Skeleton className="h-3 w-40" />
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-2/3" />
      <Skeleton className="h-6 w-5/6" />
    </div>
  );
}
