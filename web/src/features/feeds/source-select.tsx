import type { FeedSource } from "../../api/types";
import { Select } from "../../components/ui/select";
import { isSource, READER_SOURCES, sourceLabel } from "../../lib/labels";

type SourceSelectProps = {
  source?: FeedSource;
  onChange: (source: FeedSource | undefined) => void;
};

export function SourceSelect({ source, onChange }: SourceSelectProps) {
  // A link can name a source the reader does not offer, such as El País for its stored feeds.
  const offered = source === undefined || READER_SOURCES.includes(source);
  return (
    <Select
      label="Periódico"
      value={source ?? ""}
      onChange={(event) => {
        const value = event.target.value;
        onChange(isSource(value) ? value : undefined);
      }}
    >
      <option value="">Todos</option>
      {READER_SOURCES.map((value) => (
        <option key={value} value={value}>
          {sourceLabel(value)}
        </option>
      ))}
      {!offered && <option value={source}>{sourceLabel(source)}</option>}
    </Select>
  );
}
