const MAX_PATH_LENGTH = 48;

/** The article's address for display: the host without `www.` and a path shortened in the middle. */
export function shortenArticleUrl(url: string): { host: string; path: string } {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return { host: url, path: "" };
  }
  const path = parsed.pathname === "/" ? "" : parsed.pathname;
  const head = Math.floor((MAX_PATH_LENGTH - 1) / 2);
  const tail = MAX_PATH_LENGTH - 1 - head;
  return {
    host: parsed.hostname.replace(/^www\./, ""),
    path: path.length <= MAX_PATH_LENGTH ? path : `${path.slice(0, head)}…${path.slice(-tail)}`,
  };
}
