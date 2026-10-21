import { expect, it } from "vitest";
import { shortenArticleUrl } from "./urls";

it("shows the host without www and the path", () => {
  expect(shortenArticleUrl("https://www.elmundo.es/espana/noticia.html")).toEqual({
    host: "elmundo.es",
    path: "/espana/noticia.html",
  });
});

it("shortens a long path in the middle", () => {
  const { path } = shortenArticleUrl(
    "https://www.elespanol.com/invertia/vivienda/20261021/alquiler-sube-tercer-trimestre-consecutivo-grandes-ciudades/1003743.html",
  );

  expect(path).toHaveLength(48);
  expect(path.startsWith("/invertia/vivienda/")).toBe(true);
  expect(path).toContain("…");
  expect(path.endsWith("1003743.html")).toBe(true);
});

it("leaves the root path out", () => {
  expect(shortenArticleUrl("https://example.com/")).toEqual({ host: "example.com", path: "" });
});

it("shows a URL it cannot read as it comes", () => {
  expect(shortenArticleUrl("not a url")).toEqual({ host: "not a url", path: "" });
});
