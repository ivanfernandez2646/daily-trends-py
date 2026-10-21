import { describe, expect, it } from "vitest";
import { CATEGORIES, categoryLabel, READER_SOURCES, sourceLabel } from "./labels";

describe("categoryLabel", () => {
  it.each([
    ["POLITICS", "Política"],
    ["INTERNATIONAL", "Internacional"],
    ["ECONOMY", "Economía"],
    ["SOCIETY", "Sociedad"],
    ["SPORTS", "Deportes"],
    ["CULTURE", "Cultura"],
    ["TECHNOLOGY", "Tecnología"],
    ["SCIENCE", "Ciencia"],
    ["HEALTH", "Salud"],
    ["OPINION", "Opinión"],
    ["OTHER", "Otros"],
  ])("labels %s as %s", (category, label) => {
    expect(categoryLabel(category)).toBe(label);
  });

  it("shows an unknown category as it comes", () => {
    expect(categoryLabel("TRAVEL")).toBe("TRAVEL");
  });
});

describe("sourceLabel", () => {
  it.each([
    ["EL_MUNDO", "El Mundo"],
    ["EL_ESPANOL", "El Español"],
    ["EL_CONFIDENCIAL", "El Confidencial"],
    ["LA_RAZON", "La Razón"],
    ["LA_VANGUARDIA", "La Vanguardia"],
    ["EL_PAIS", "El País"],
    ["CMS", "Redacción"],
  ])("labels %s as %s", (source, label) => {
    expect(sourceLabel(source)).toBe(label);
  });

  it("shows an unknown source as it comes", () => {
    expect(sourceLabel("ABC")).toBe("ABC");
  });
});

it("lists the categories in the order of the design system", () => {
  expect(CATEGORIES).toEqual([
    "POLITICS",
    "INTERNATIONAL",
    "ECONOMY",
    "SOCIETY",
    "SPORTS",
    "CULTURE",
    "TECHNOLOGY",
    "SCIENCE",
    "HEALTH",
    "OPINION",
    "OTHER",
  ]);
});

it("offers the scraped newspapers and then the newsroom", () => {
  expect(READER_SOURCES).toEqual([
    "EL_MUNDO",
    "EL_ESPANOL",
    "EL_CONFIDENCIAL",
    "LA_RAZON",
    "LA_VANGUARDIA",
    "CMS",
  ]);
});
