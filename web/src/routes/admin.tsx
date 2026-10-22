import { createFileRoute, Outlet, redirect, useNavigate, useRouter } from "@tanstack/react-router";
import { useEffect } from "react";
import { AdminLayout } from "../features/admin/admin-layout";
import { useSession } from "../features/session/session-context";

export const Route = createFileRoute("/admin")({
  beforeLoad: async ({ context: { session }, location }) => {
    await session.restore();
    if (session.state().status !== "active") {
      throw redirect({ to: "/login", search: { redirect: location.href } });
    }
  },
  component: AdminRoute,
});

function AdminRoute() {
  const session = useSession();
  const router = useRouter();
  const navigate = useNavigate();

  // The session ends before a write can fail. Unsaved changes do not hold the user back: the
  // token is gone, so they could not be saved anyway.
  useEffect(
    () =>
      session.onEnd((reason) => {
        if (reason === "expired") {
          void navigate({
            to: "/login",
            search: { redirect: router.state.location.href },
            ignoreBlocker: true,
          });
        }
      }),
    [session, router, navigate],
  );

  return (
    <AdminLayout>
      <Outlet />
    </AdminLayout>
  );
}
