import type { FeedCategory } from "../../api/types";
import { Chip } from "../../components/ui/chip";
import { CATEGORIES, categoryLabel } from "../../lib/labels";

type CategoryChipsProps = {
  category?: FeedCategory;
  onChange: (category: FeedCategory | undefined) => void;
};

/** One category at a time; *Todas* shows them all. */
export function CategoryChips({ category, onChange }: CategoryChipsProps) {
  return (
    <fieldset className="flex flex-wrap gap-2">
      <legend className="sr-only">Categoría</legend>
      <Chip pressed={category === undefined} onPressedChange={() => onChange(undefined)}>
        Todas
      </Chip>
      {CATEGORIES.map((value) => (
        <Chip
          key={value}
          pressed={category === value}
          onPressedChange={(pressed) => onChange(pressed ? value : undefined)}
        >
          {categoryLabel(value)}
        </Chip>
      ))}
    </fieldset>
  );
}
