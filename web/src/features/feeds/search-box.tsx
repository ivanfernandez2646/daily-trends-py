import { Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useDebouncedValue } from "../../lib/use-debounced-value";

const SEARCH_DELAY_MS = 300;
const MAX_SEARCH_LENGTH = 100;

type SearchBoxProps = {
  q?: string;
  onSearch: (q: string | undefined) => void;
  /** The reader came to search, from *Buscar*. */
  focused?: boolean;
};

/** Applies 300 ms after the last keystroke, or at once on Enter; an empty box removes `q`. */
export function SearchBox({ q = "", onSearch, focused = false }: SearchBoxProps) {
  const [text, setText] = useState(q);
  const applied = useRef(q);
  const input = useRef<HTMLInputElement>(null);
  const settled = useDebouncedValue(text, SEARCH_DELAY_MS);

  const apply = (value: string) => {
    const search = value.trim();
    if (search !== applied.current) {
      applied.current = search;
      onSearch(search === "" ? undefined : search);
    }
  };

  // biome-ignore lint/correctness/useExhaustiveDependencies: only a settled text applies the search.
  useEffect(() => apply(settled), [settled]);

  // The URL changed without typing, such as going back or clearing the filters.
  useEffect(() => {
    if (q !== applied.current) {
      applied.current = q;
      setText(q);
    }
  }, [q]);

  useEffect(() => {
    if (focused) {
      input.current?.focus();
    }
  }, [focused]);

  return (
    <search>
      <form
        className="flex flex-col gap-1.5"
        onSubmit={(event) => {
          event.preventDefault();
          apply(text);
        }}
      >
        <label htmlFor="buscar" className="text-xs font-semibold text-ink-soft">
          Buscar noticias
        </label>
        <div className="flex h-11 items-center gap-2.5 rounded-field border border-field-border bg-surface px-3.5 focus-within:outline-2 focus-within:outline-offset-3 focus-within:outline-accent">
          <Search aria-hidden="true" className="size-4 shrink-0 text-meta" />
          <input
            ref={input}
            id="buscar"
            type="search"
            maxLength={MAX_SEARCH_LENGTH}
            value={text}
            onChange={(event) => setText(event.target.value)}
            className="min-w-0 flex-1 bg-transparent text-ink outline-none placeholder:text-meta"
            placeholder="Palabras del titular o la entradilla"
          />
        </div>
      </form>
    </search>
  );
}
