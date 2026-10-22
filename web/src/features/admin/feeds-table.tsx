import { Link } from "@tanstack/react-router";
import { Pencil, Trash2 } from "lucide-react";
import type { FeedResponse } from "../../api/types";
import { Button, IconButton } from "../../components/ui/button";
import { CategoryLabel } from "../../components/ui/category-label";
import { Skeleton } from "../../components/ui/skeleton";
import { formatFullDate, formatTimeColumn } from "../../lib/dates";
import { sourceLabel } from "../../lib/labels";

type FeedsTableProps = {
  feeds: FeedResponse[];
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
  onDelete: (feed: FeedResponse) => void;
};

const HEADER = "px-4 py-3 text-left text-label text-meta uppercase";
const CELL = "px-4 py-2 align-middle";

/** Every feed, in a panel that scrolls sideways on narrow screens instead of the page. */
export function FeedsTable({ feeds, hasMore, loadingMore, onLoadMore, onDelete }: FeedsTableProps) {
  return (
    <div className="rounded-card border border-rule bg-surface">
      {/* Positioned, so the hidden column title scrolls with the table instead of widening the page. */}
      <div className="relative overflow-x-auto">
        <table aria-label="Noticias" className="w-full min-w-[720px] border-collapse text-sm">
          <thead className="border-b border-rule">
            <tr>
              <th scope="col" className={HEADER}>
                Titular
              </th>
              <th scope="col" className={HEADER}>
                Periódico
              </th>
              <th scope="col" className={HEADER}>
                Categoría
              </th>
              <th scope="col" className={HEADER}>
                Fecha
              </th>
              <th scope="col" className={HEADER}>
                <span className="sr-only">Acciones</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {feeds.map((feed) => {
              const { day, time } = formatTimeColumn(feed.created_at);
              return (
                <tr key={feed.id} className="border-b border-rule last:border-b-0">
                  <td className={`${CELL} max-w-md`}>
                    <Link
                      to="/feeds/$id"
                      params={{ id: feed.id }}
                      className="font-serif text-body font-medium hover:text-accent"
                    >
                      {feed.title}
                    </Link>
                  </td>
                  <td className={`${CELL} whitespace-nowrap text-ink-soft`}>
                    {sourceLabel(feed.source)}
                  </td>
                  <td className={`${CELL} whitespace-nowrap`}>
                    <CategoryLabel category={feed.category} />
                  </td>
                  <td className={`${CELL} whitespace-nowrap text-meta`}>
                    <time dateTime={feed.created_at} title={formatFullDate(feed.created_at)}>
                      {day}, {time}
                    </time>
                  </td>
                  <td className={`${CELL} whitespace-nowrap text-right`}>
                    <IconButton asChild label={`Editar «${feed.title}»`}>
                      <Link to="/admin/feeds/$id/edit" params={{ id: feed.id }}>
                        <Pencil aria-hidden="true" />
                      </Link>
                    </IconButton>
                    <IconButton
                      label={`Borrar «${feed.title}»`}
                      className="hover:text-danger"
                      onClick={() => onDelete(feed)}
                    >
                      <Trash2 aria-hidden="true" />
                    </IconButton>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {hasMore && (
        <div className="flex justify-center border-t border-rule p-4">
          <Button variant="secondary" size="dense" onClick={onLoadMore} disabled={loadingMore}>
            {loadingMore ? "Cargando…" : "Cargar más"}
          </Button>
        </div>
      )}
    </div>
  );
}

export function FeedsTableSkeleton() {
  return (
    <div role="status" className="rounded-card border border-rule bg-surface">
      <span className="sr-only">Cargando noticias</span>
      {[0, 1, 2, 3, 4].map((index) => (
        <div key={index} className="flex gap-6 border-b border-rule px-4 py-4 last:border-b-0">
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-20" />
        </div>
      ))}
    </div>
  );
}
