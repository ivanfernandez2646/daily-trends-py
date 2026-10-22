import type { CreateFeedRequest, FeedCategory, FeedResponse } from "../../api/types";

/** What the feed form holds, as typed: the API's values are trimmed out of it. */
export type FeedFormValues = {
  title: string;
  description: string;
  author: string;
  category: FeedCategory | undefined;
};

export type FeedFormErrors = Partial<Record<"title" | "author" | "category", string>>;

export const EMPTY_FEED_FORM: FeedFormValues = {
  title: "",
  description: "",
  author: "",
  category: undefined,
};

/** The fields the API would reject, with what to do about them; empty when the form is valid. */
export function validateFeedForm({ title, author, category }: FeedFormValues): FeedFormErrors {
  return {
    ...(title.trim() === "" && { title: "Escribe un titular" }),
    ...(author.trim() === "" && { author: "Escribe el autor" }),
    ...(category === undefined && { category: "Elige una categoría" }),
  };
}

/** The body of `PUT /feed/{id}` for a valid form; a blank description is left out. */
export function toCreateRequest(
  values: FeedFormValues & { category: FeedCategory },
): CreateFeedRequest {
  const description = values.description.trim();
  return {
    title: values.title.trim(),
    author: values.author.trim(),
    category: values.category,
    ...(description !== "" && { description }),
  };
}

type PreviewBase = Pick<FeedResponse, "id" | "source" | "url" | "created_at" | "updated_at">;

/** The feed as the front page would show it with these values; blank fields show what goes there. */
export function previewFeed(values: FeedFormValues, base: PreviewBase): FeedResponse {
  return {
    ...base,
    title: values.title.trim() || "Titular de la noticia",
    description: values.description.trim() || null,
    author: values.author.trim() || "Autor",
    category: values.category ?? "OTHER",
  };
}
