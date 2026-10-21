import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SourceLink } from "./source-link";

const URL = "https://www.elmundo.es/espana/noticia.html";

describe.each(["link", "button"] as const)("as a %s", (variant) => {
  it("opens the original article in a new tab and says so", () => {
    render(<SourceLink url={URL} source="EL_MUNDO" variant={variant} />);

    const link = screen.getByRole("link", {
      name: "Leer en El Mundo (se abre en una pestaña nueva)",
    });
    expect(link).toHaveAttribute("href", URL);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });
});

it("names the feed's source even when the article is on another site", () => {
  render(<SourceLink url="https://example.com/nota" source="LA_RAZON" />);

  expect(screen.getByRole("link", { name: /^Leer en La Razón/ })).toHaveAttribute(
    "href",
    "https://example.com/nota",
  );
});
