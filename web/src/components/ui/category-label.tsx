import { categoryLabel } from "../../lib/labels";
import { cn } from "../../lib/utils";

type CategoryLabelProps = { category: string; className?: string };

export function CategoryLabel({ category, className }: CategoryLabelProps) {
  // The marker color is never the only cue: the label is always there, in ink.
  const marker = `var(--category-${category.toLowerCase()}, var(--category-other))`;
  return (
    <span className={cn("inline-flex items-center gap-2 text-label text-ink uppercase", className)}>
      <span aria-hidden="true" className="size-2 shrink-0" style={{ backgroundColor: marker }} />
      {categoryLabel(category)}
    </span>
  );
}
