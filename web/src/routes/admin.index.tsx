import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/admin/")({
  component: FeedsAdminPage,
});

function FeedsAdminPage() {
  return <h1 className="font-serif text-title-1">Noticias</h1>;
}
