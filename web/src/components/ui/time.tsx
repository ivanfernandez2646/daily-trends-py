import { formatFullDate, formatRelative } from "../../lib/dates";

type TimeProps = { iso: string; format?: "relative" | "full"; className?: string };

export function Time({ iso, format = "relative", className }: TimeProps) {
  const full = formatFullDate(iso);
  return (
    <time dateTime={iso} title={full} className={className}>
      {format === "full" ? full : formatRelative(iso)}
    </time>
  );
}
