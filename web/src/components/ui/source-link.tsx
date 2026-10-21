import { ArrowUpRight } from "lucide-react";
import { sourceLabel } from "../../lib/labels";
import { cn } from "../../lib/utils";
import { Button } from "./button";

type SourceLinkProps = {
  url: string;
  /** The feed's source, which names the link even when the article is on another site. */
  source: string;
  variant?: "link" | "button";
  className?: string;
};

export function SourceLink({ url, source, variant = "link", className }: SourceLinkProps) {
  return (
    <Button
      asChild
      variant={variant === "button" ? "primary" : "link"}
      className={cn(variant === "button" && "h-12 px-6", className)}
    >
      <a href={url} target="_blank" rel="noopener noreferrer">
        Leer en {sourceLabel(source)}{" "}
        <span className="sr-only">(se abre en una pestaña nueva)</span>
        <ArrowUpRight aria-hidden="true" />
      </a>
    </Button>
  );
}
