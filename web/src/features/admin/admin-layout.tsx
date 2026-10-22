import { Link, useNavigate } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Button } from "../../components/ui/button";
import { formatClock } from "../../lib/dates";
import { useSession, useSessionState } from "../session/session-context";

const MENU_LINK =
  "flex min-h-11 items-center rounded-field px-3 text-sm font-medium text-ink-soft transition-colors duration-150 ease-out hover:bg-canvas hover:text-ink data-[status=active]:bg-canvas data-[status=active]:text-ink";

/** The CMS: a side menu with the session, stacked above the content on narrow screens. */
export function AdminLayout({ children }: { children: ReactNode }) {
  const session = useSession();
  const { admin } = useSessionState();
  const navigate = useNavigate();

  const logOut = () => {
    session.end("logout");
    void navigate({ to: "/" });
  };

  return (
    <div className="min-h-screen bg-canvas md:grid md:grid-cols-[240px_minmax(0,1fr)]">
      <aside
        aria-label="Menú del CMS"
        className="flex flex-col gap-6 border-b border-rule bg-surface p-5 md:sticky md:top-0 md:h-screen md:border-r md:border-b-0"
      >
        <div className="flex items-baseline gap-2">
          <Link to="/admin" className="font-serif text-[24px] font-medium tracking-[-0.02em]">
            Daily Trends
          </Link>
          <span className="text-label text-meta uppercase">CMS</span>
        </div>

        <nav aria-label="CMS">
          <ul className="flex gap-1 md:flex-col">
            <li>
              <Link to="/admin" activeOptions={{ includeSearch: false }} className={MENU_LINK}>
                Noticias
              </Link>
            </li>
            <li>
              <Link to="/" activeOptions={{ exact: true }} className={MENU_LINK}>
                Ver el sitio
              </Link>
            </li>
          </ul>
        </nav>

        {admin !== undefined && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-rule pt-4 md:mt-auto md:flex-col md:items-start">
            <div className="min-w-0 text-caption">
              <p className="truncate font-semibold text-ink">{admin.email}</p>
              <p className="text-meta">Sesión hasta las {formatClock(admin.expiresAt)}</p>
            </div>
            <Button variant="secondary" size="dense" onClick={logOut}>
              Cerrar sesión
            </Button>
          </div>
        )}
      </aside>

      <main className="min-w-0 px-4 py-8 sm:px-8">{children}</main>
    </div>
  );
}
