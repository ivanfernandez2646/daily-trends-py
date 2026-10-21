import { Link } from "@tanstack/react-router";
import { ChevronDown, Menu, Search } from "lucide-react";
import { useId, useState } from "react";
import type { FeedCategory } from "../../api/types";
import { CategoryMarker } from "../../components/ui/category-label";
import { formatRelative, formatToday } from "../../lib/dates";
import { CATEGORIES, categoryLabel } from "../../lib/labels";
import { cn } from "../../lib/utils";

const SHORTCUTS: readonly FeedCategory[] = [
  "POLITICS",
  "INTERNATIONAL",
  "ECONOMY",
  "SPORTS",
  "CULTURE",
  "TECHNOLOGY",
];

const NAV_LINK =
  "transition-colors duration-150 ease-out hover:text-accent data-[status=active]:text-accent data-[status=active]:shadow-[inset_0_-2px_0_var(--color-accent)]";

type ReaderHeaderProps =
  | { variant: "front" /** The newest feed of the front page. */; updatedAt?: string }
  | { variant: "compact"; updatedAt?: never };

export function ReaderHeader(props: ReaderHeaderProps) {
  return props.variant === "front" ? (
    <FrontHeader updatedAt={props.updatedAt} />
  ) : (
    <CompactHeader />
  );
}

function FrontHeader({ updatedAt }: { updatedAt?: string }) {
  const [sectionsOpen, setSectionsOpen] = useState(false);
  const sectionsId = useId();
  const toggleSections = () => setSectionsOpen((open) => !open);
  const today = formatToday();

  return (
    <header>
      <div className="flex flex-wrap items-center justify-between gap-3 py-3.5 text-caption text-meta">
        <span>{today.charAt(0).toUpperCase() + today.slice(1)}</span>
        {updatedAt !== undefined && (
          <span className="inline-flex items-center gap-2">
            <span aria-hidden="true" className="size-1.5 rounded-full bg-success-fg" />
            Actualizado {formatRelative(updatedAt)}
          </span>
        )}
      </div>

      <div className="border-t border-ink pt-5 pb-5 sm:pt-7 sm:pb-6 sm:text-center">
        <div className="flex items-center justify-between gap-2 sm:justify-center">
          <h1 className="font-serif text-masthead">
            <Link to="/">Daily Trends</Link>
          </h1>
          <div className="flex sm:hidden">
            <Link
              to="/feeds"
              aria-label="Buscar"
              className="grid size-11 place-items-center hover:text-accent"
            >
              <Search aria-hidden="true" className="size-5" />
            </Link>
            <button
              type="button"
              aria-label="Menú"
              aria-expanded={sectionsOpen}
              aria-controls={sectionsId}
              onClick={toggleSections}
              className="grid size-11 place-items-center hover:text-accent"
            >
              <Menu aria-hidden="true" className="size-5" />
            </button>
          </div>
        </div>
        <p className="mt-2.5 text-meta">Los titulares de la prensa española, en un solo lugar.</p>
      </div>

      <nav aria-label="Secciones" className="border-y border-rule text-sm font-medium">
        <div className="hidden flex-wrap items-center justify-between gap-3 py-3 sm:flex">
          <ul aria-label="Secciones destacadas" className="flex flex-wrap gap-x-6 gap-y-2">
            <li>
              <Link to="/" activeOptions={{ exact: true }} className={cn(NAV_LINK, "pb-1")}>
                Portada
              </Link>
            </li>
            {SHORTCUTS.map((category) => (
              <li key={category}>
                <Link to="/feeds" search={{ category }} className="hover:text-accent">
                  {categoryLabel(category)}
                </Link>
              </li>
            ))}
            <li>
              <Link to="/feeds" className="text-meta hover:text-accent">
                Todas las secciones
              </Link>
            </li>
          </ul>
          <Link to="/feeds" className="inline-flex min-h-11 items-center gap-2 hover:text-accent">
            <Search aria-hidden="true" className="size-4" />
            Buscar
          </Link>
        </div>

        <div className="sm:hidden">
          <div className="flex items-center justify-between gap-3 py-1">
            <span className="text-label text-meta uppercase">Portada</span>
            <button
              type="button"
              aria-expanded={sectionsOpen}
              aria-controls={sectionsId}
              onClick={toggleSections}
              className="inline-flex min-h-11 items-center gap-1.5 font-semibold"
            >
              Secciones
              <ChevronDown
                aria-hidden="true"
                className={cn("size-4 transition-transform", sectionsOpen && "rotate-180")}
              />
            </button>
          </div>
          {sectionsOpen && (
            <ul
              id={sectionsId}
              aria-label="Todas las secciones"
              className="grid grid-cols-2 gap-x-4 pb-4"
            >
              {CATEGORIES.map((category) => (
                <li key={category} className="border-t border-rule">
                  <Link
                    to="/feeds"
                    search={{ category }}
                    className="flex min-h-11 items-center gap-2.5"
                  >
                    <CategoryMarker category={category} />
                    {categoryLabel(category)}
                  </Link>
                </li>
              ))}
              <li className="border-t border-rule">
                <Link to="/feeds" className="flex min-h-11 items-center">
                  Todas las noticias
                </Link>
              </li>
            </ul>
          )}
        </div>
      </nav>
    </header>
  );
}

function CompactHeader() {
  return (
    <header className="border-b border-rule">
      <div className="flex min-h-18 flex-wrap items-center justify-between gap-4">
        <Link to="/" className="font-serif text-[28px] font-medium tracking-[-0.02em]">
          Daily Trends
        </Link>
        <nav aria-label="Principal">
          <ul className="flex items-center gap-7 text-sm font-medium">
            <li>
              <Link to="/" activeOptions={{ exact: true }} className={cn(NAV_LINK, "pb-1")}>
                Portada
              </Link>
            </li>
            <li>
              <Link
                to="/feeds"
                activeOptions={{ includeSearch: false }}
                className={cn(NAV_LINK, "pb-1")}
              >
                Explorar
              </Link>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
}
