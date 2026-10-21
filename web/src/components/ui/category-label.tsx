import { categoryLabel } from "../../lib/labels";
import { cn } from "../../lib/utils";

type CategoryLabelProps = { category: string; className?: string };

export function CategoryLabel({ category, className }: CategoryLabelProps) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-label text-ink uppercase", className)}>
      <CategoryMarker category={category} />
      {categoryLabel(category)}
    </span>
  );
}

/** The category's color square. Never the only cue: its label always goes next to it, in ink. */
export function CategoryMarker({ category }: { category: string }) {
  const color = `var(--category-${category.toLowerCase()}, var(--category-other))`;
  return <span aria-hidden="true" className="size-2 shrink-0" style={{ backgroundColor: color }} />;
}
