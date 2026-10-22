import { useId } from "react";
import type { FeedCategory } from "../../api/types";
import { CategoryMarker } from "../../components/ui/category-label";
import { Chip } from "../../components/ui/chip";
import { CATEGORIES, categoryLabel } from "../../lib/labels";

type CategoryPickerProps = {
  category: FeedCategory | undefined;
  onChange: (category: FeedCategory) => void;
  error?: string;
};

/** The category of a feed: always exactly one once chosen, so pressing it again keeps it. */
export function CategoryPicker({ category, onChange, error }: CategoryPickerProps) {
  const errorId = useId();
  return (
    <fieldset
      aria-describedby={error === undefined ? undefined : errorId}
      className="flex flex-col gap-1.5"
    >
      <legend className="mb-1.5 text-xs font-semibold text-ink-soft">Categoría</legend>
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((value) => (
          <Chip key={value} pressed={category === value} onPressedChange={() => onChange(value)}>
            <CategoryMarker category={value} />
            {categoryLabel(value)}
          </Chip>
        ))}
      </div>
      {error !== undefined && (
        <p id={errorId} className="text-caption text-error-fg">
          {error}
        </p>
      )}
    </fieldset>
  );
}
