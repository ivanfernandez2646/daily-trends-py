import type { components } from "./schema.gen";

type Schemas = components["schemas"];

export type FeedResponse = Schemas["FeedResponse"];
export type FeedCategory = Schemas["FeedCategory"];
export type FeedSource = Schemas["FeedSource"];
export type FeedPageResponse = Schemas["FeedPageResponse"];
export type AdminSessionResponse = Schemas["AdminSessionResponse"];
export type CreateFeedRequest = Schemas["CreateFeedRequest"];
export type UpdateFeedRequest = Schemas["UpdateFeedRequest"];

/** The filters of `GET /feed/list`, as the browse page keeps them in its URL. */
export type FeedFilters = { category?: FeedCategory; source?: FeedSource; q?: string };
