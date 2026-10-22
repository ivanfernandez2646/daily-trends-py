import { describe, expect, it } from "vitest";
import { type FeedFormValues, toCreateRequest, validateFeedForm } from "./feed-form-values";

const VALID = {
  title: "El alquiler sube por tercer trimestre",
  description: "Madrid y Barcelona concentran las subidas.",
  author: "Laura Martín",
  category: "ECONOMY",
} satisfies FeedFormValues;

describe("validateFeedForm", () => {
  it("accepts a title, an author and a category, without a description", () => {
    expect(validateFeedForm({ ...VALID, description: "" })).toEqual({});
  });

  it("asks for each missing field in Spanish", () => {
    expect(
      validateFeedForm({ title: "", description: "", author: "", category: undefined }),
    ).toEqual({
      title: "Escribe un titular",
      author: "Escribe el autor",
      category: "Elige una categoría",
    });
  });

  it("treats a title or an author of spaces as missing", () => {
    expect(validateFeedForm({ ...VALID, title: "   ", author: "\t " })).toEqual({
      title: "Escribe un titular",
      author: "Escribe el autor",
    });
  });
});

describe("toCreateRequest", () => {
  it("sends the values without surrounding spaces", () => {
    expect(
      toCreateRequest({
        title: "  El alquiler sube ",
        description: " Madrid y Barcelona. ",
        author: " Laura Martín ",
        category: "ECONOMY",
      }),
    ).toEqual({
      title: "El alquiler sube",
      description: "Madrid y Barcelona.",
      author: "Laura Martín",
      category: "ECONOMY",
    });
  });

  it("leaves out a blank description", () => {
    expect(toCreateRequest({ ...VALID, description: "  " })).not.toHaveProperty("description");
  });
});
