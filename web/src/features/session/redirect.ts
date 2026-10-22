const HOME = "/admin";

/**
 * Where to go after logging in: a path of this app, else `/admin`. Browsers read `//` and `/\` as
 * the start of another site's address, so neither is a path of the app.
 */
export function safeRedirect(value: unknown): string {
  if (typeof value !== "string" || !value.startsWith("/") || /^\/[/\\]/.test(value)) {
    return HOME;
  }
  return value;
}
