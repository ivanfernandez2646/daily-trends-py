import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({ component: FrontPage });

function FrontPage() {
  return (
    <main>
      <h1>Daily Trends</h1>
    </main>
  );
}
