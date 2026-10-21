import { Link } from "@tanstack/react-router";
import type { FeedResponse } from "../../api/types";
import { CategoryLabel } from "../../components/ui/category-label";
import { SourceLink } from "../../components/ui/source-link";
import { Time } from "../../components/ui/time";
import { formatTimeColumn } from "../../lib/dates";
import { sourceLabel } from "../../lib/labels";
import { cn } from "../../lib/utils";

type Variant = "lead" | "side" | "grid" | "row" | "compact";

type FeedCardProps = {
  feed: FeedResponse;
  variant: Variant;
  /** Defaults to the level each variant has on the reader's pages. */
  headingLevel?: 2 | 3;
};

const DEFAULT_HEADING_LEVEL: Record<Variant, 2 | 3> = {
  lead: 2,
  side: 3,
  grid: 3,
  row: 2,
  compact: 2,
};

const ARTICLE_CLASS: Record<Variant, string> = {
  lead: "gap-4",
  side: "gap-2 border-b border-rule py-5",
  grid: "gap-2.5 border-t border-ink py-6",
  row: "gap-2",
  compact: "gap-1.5 border-b border-rule py-4",
};

const HEADLINE_CLASS: Record<Variant, string> = {
  lead: "text-display",
  side: "text-title-2",
  grid: "text-title-2",
  row: "text-title-2",
  compact: "text-xl leading-tight",
};

export function FeedCard({ feed, variant, headingLevel }: FeedCardProps) {
  const Heading = `h${headingLevel ?? DEFAULT_HEADING_LEVEL[variant]}` as const;
  const showsDescription = variant === "lead" || variant === "grid" || variant === "row";
  const showsAuthor = showsDescription;
  const showsTime = variant !== "row";

  const card = (
    <article className={cn("flex min-w-0 flex-col", ARTICLE_CLASS[variant])}>
      <CategoryLabel category={feed.category} />
      <Heading className={cn("font-serif text-ink", HEADLINE_CLASS[variant])}>
        <Link
          to="/feeds/$id"
          params={{ id: feed.id }}
          className="transition-colors duration-150 ease-out hover:text-accent"
        >
          {feed.title}
        </Link>
      </Heading>
      {showsDescription && feed.description !== null && (
        <p
          className={cn(
            "text-ink-soft",
            variant === "lead" ? "max-w-[60ch] font-serif text-lead" : "max-w-[72ch]",
            variant === "grid" && "line-clamp-2",
          )}
        >
          {feed.description}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <div className="text-caption text-meta">
          <span className="font-serif text-[15px] font-medium text-ink">
            {sourceLabel(feed.source)}
          </span>
          {showsAuthor && ` · ${feed.author}`}
          {showsTime && (
            <>
              {" · "}
              <Time iso={feed.created_at} />
            </>
          )}
        </div>
        {variant === "lead" && feed.url !== null && (
          <SourceLink url={feed.url} source={feed.source} className="text-sm" />
        )}
      </div>
    </article>
  );

  if (variant !== "row") {
    return card;
  }
  const { time, day } = formatTimeColumn(feed.created_at);
  return (
    <div className="grid grid-cols-[5rem_minmax(0,1fr)] gap-4 border-t border-rule py-6 sm:grid-cols-[7.5rem_minmax(0,1fr)] sm:gap-8">
      <p className="flex flex-col gap-0.5 text-caption text-meta">
        <time dateTime={feed.created_at} className="font-medium text-ink">
          {time}
        </time>
        <span>{day}</span>
      </p>
      {card}
    </div>
  );
}
