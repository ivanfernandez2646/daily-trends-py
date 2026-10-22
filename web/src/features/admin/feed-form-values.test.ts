import { describe, expect, it } from "vitest";
import { aFeed } from "../../test/feed-mother";
import {
  type FeedFormValues,
  formFromFeed,
  toCreateRequest,
  toUpdateRequest,
  validateFeedForm,
} from "./feed-form-values";

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

describe("toUpdateRequest", () => {
  const original = aFeed({
    title: "El alquiler sube",
    description: "Madrid y Barcelona.",
    category: "ECONOMY",
  });

  it("sends nothing for the values the feed already has, spaces aside", () => {
    expect(toUpdateRequest(original, formFromFeed(original))).toEqual({});
    expect(
      toUpdateRequest(original, { ...formFromFeed(original), title: " El alquiler sube  " }),
    ).toEqual({});
  });

  it("sends only the fields that changed, trimmed", () => {
    expect(
      toUpdateRequest(original, {
        ...formFromFeed(original),
        title: " El alquiler baja ",
        category: "SOCIETY",
      }),
    ).toEqual({ title: "El alquiler baja", category: "SOCIETY" });
  });

  it("clears the description with null when it is emptied", () => {
    expect(toUpdateRequest(original, { ...formFromFeed(original), description: "  " })).toEqual({
      description: null,
    });
  });

  it("sends nothing for a blank description the feed did not have", () => {
    const withoutDescription = aFeed({ description: null });

    expect(toUpdateRequest(withoutDescription, formFromFeed(withoutDescription))).toEqual({});
  });

  it("sends a description the feed did not have", () => {
    const withoutDescription = aFeed({ description: null });

    expect(
      toUpdateRequest(withoutDescription, {
        ...formFromFeed(withoutDescription),
        description: "Nueva entradilla",
      }),
    ).toEqual({ description: "Nueva entradilla" });
  });
});
