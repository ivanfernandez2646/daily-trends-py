import { render } from "@testing-library/react";
import { expect, it } from "vitest";
import { Skeleton } from "./skeleton";

it("is hidden from assistive technology", () => {
  const { container } = render(<Skeleton className="h-4 w-1/2" />);

  expect(container.firstElementChild).toHaveAttribute("aria-hidden", "true");
});
