import { createFileRoute } from "@tanstack/react-router";

// The feed's page: its content comes with the detail screen (S14, phase 5).
export const Route = createFileRoute("/feeds/$id")({ component: FeedPage });

function FeedPage() {
  return (
    <main>
      <h1>Noticia</h1>
    </main>
  );
}
