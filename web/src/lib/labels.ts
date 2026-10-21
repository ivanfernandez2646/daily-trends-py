import type { FeedCategory, FeedSource } from "../api/types";

const CATEGORY_LABELS: Record<FeedCategory, string> = {
  POLITICS: "Política",
  INTERNATIONAL: "Internacional",
  ECONOMY: "Economía",
  SOCIETY: "Sociedad",
  SPORTS: "Deportes",
  CULTURE: "Cultura",
  TECHNOLOGY: "Tecnología",
  SCIENCE: "Ciencia",
  HEALTH: "Salud",
  OPINION: "Opinión",
  OTHER: "Otros",
};

const SOURCE_LABELS: Record<FeedSource, string> = {
  EL_MUNDO: "El Mundo",
  EL_ESPANOL: "El Español",
  EL_CONFIDENCIAL: "El Confidencial",
  LA_RAZON: "La Razón",
  LA_VANGUARDIA: "La Vanguardia",
  EL_PAIS: "El País",
  CMS: "Redacción",
};

export const CATEGORIES = Object.keys(CATEGORY_LABELS) as readonly FeedCategory[];

/** The newspapers a reader can pick: the scraped ones and the newsroom. */
export const READER_SOURCES: readonly FeedSource[] = [
  "EL_MUNDO",
  "EL_ESPANOL",
  "EL_CONFIDENCIAL",
  "LA_RAZON",
  "LA_VANGUARDIA",
  "CMS",
];

export function isCategory(value: string): value is FeedCategory {
  return Object.hasOwn(CATEGORY_LABELS, value);
}

export function isSource(value: string): value is FeedSource {
  return Object.hasOwn(SOURCE_LABELS, value);
}

/** The Spanish label; a value the app does not know yet shows as it comes. */
export function categoryLabel(value: string): string {
  return isCategory(value) ? CATEGORY_LABELS[value] : value;
}

export function sourceLabel(value: string): string {
  return isSource(value) ? SOURCE_LABELS[value] : value;
}
