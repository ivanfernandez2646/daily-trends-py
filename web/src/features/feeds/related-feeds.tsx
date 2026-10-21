import { Link } from "@tanstack/react-router";
import type { FeedResponse } from "../../api/types";
import { Time } from "../../components/ui/time";
import { categoryLabel, sourceLabel } from "../../lib/labels";

type RelatedFeedsProps = { category: string; feeds: FeedResponse[] };

export function RelatedFeeds({ category, feeds }: RelatedFeedsProps) {
  return (
    <section aria-labelledby="related-feeds" className="mt-16">
      <h2 id="related-feeds" className="mb-2 font-serif text-title-2">
        Más de {categoryLabel(category)}
      </h2>
      <ul>
        {feeds.map((feed) => (
          <li key={feed.id} className="border-t border-rule py-4">
            <Link
              to="/feeds/$id"
              params={{ id: feed.id }}
              className="font-serif text-[19px] font-medium leading-snug hover:text-accent"
            >
              {feed.title}
            </Link>
            <p className="mt-1 text-caption text-meta">
              {sourceLabel(feed.source)} · <Time iso={feed.created_at} />
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
