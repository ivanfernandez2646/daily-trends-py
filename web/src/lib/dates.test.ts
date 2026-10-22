import { describe, expect, it } from "vitest";
import {
  formatClock,
  formatFullDate,
  formatRelative,
  formatTimeColumn,
  formatToday,
} from "./dates";

const NOW = new Date("2026-10-21T10:00:00Z"); // 12:00 in Madrid

describe("formatRelative", () => {
  it.each([
    ["2026-10-21T09:59:30Z", "ahora"],
    ["2026-10-21T10:00:20Z", "ahora"],
    ["2026-10-21T09:46:00Z", "hace 14 min"],
    ["2026-10-21T09:00:01Z", "hace 59 min"],
    ["2026-10-21T08:00:00Z", "hace 2 h"],
    ["2026-10-20T10:00:01Z", "hace 23 h"],
    ["2026-10-20T10:00:00Z", "20 oct"],
    ["2026-09-03T10:00:00Z", "3 sept"],
    ["2025-12-31T10:00:00Z", "31 dic 2025"],
  ])("shows %s as %s", (iso, expected) => {
    expect(formatRelative(iso, NOW)).toBe(expected);
  });

  it("decides the year in Madrid", () => {
    const newYearsDayInMadrid = new Date("2026-01-01T00:30:00+01:00");

    expect(formatRelative("2024-12-31T23:30:00Z", newYearsDayInMadrid)).toBe("1 ene 2025");
  });
});

describe("formatTimeColumn", () => {
  it("shows today's feeds with Hoy and the time in Madrid", () => {
    expect(formatTimeColumn("2026-10-21T06:15:00Z", NOW)).toEqual({ time: "08:15", day: "Hoy" });
  });

  it("counts a late UTC evening as the next day in Madrid", () => {
    expect(formatTimeColumn("2026-10-20T22:30:00Z", NOW)).toEqual({ time: "00:30", day: "Hoy" });
  });

  it("shows yesterday's feeds with Ayer", () => {
    expect(formatTimeColumn("2026-10-20T21:59:00Z", NOW)).toEqual({ time: "23:59", day: "Ayer" });
  });

  it("shows older feeds with their day", () => {
    expect(formatTimeColumn("2026-10-18T09:00:00Z", NOW)).toEqual({
      time: "11:00",
      day: "18 oct",
    });
  });

  it("keeps Ayer across the change to winter time", () => {
    const afterTheChange = new Date("2026-10-26T09:00:00Z");

    expect(formatTimeColumn("2026-10-25T08:00:00Z", afterTheChange)).toEqual({
      time: "09:00",
      day: "Ayer",
    });
  });
});

it("formats the full date and time in Madrid", () => {
  expect(formatFullDate("2026-10-20T06:15:00Z")).toBe("20 de octubre de 2026 a las 08:15");
});

it("formats today's date in Madrid for the top bar", () => {
  expect(formatToday(new Date("2026-10-20T22:30:00Z"))).toBe("miércoles, 21 de octubre de 2026");
});

describe("formatClock", () => {
  it.each([
    ["2026-10-21T16:05:00Z", "18:05"],
    ["2026-10-25T00:30:00Z", "02:30"],
    ["2026-10-25T01:30:00Z", "02:30"],
    ["2026-10-25T02:30:00Z", "03:30"],
  ])("shows %s as %s in Madrid", (iso, clock) => {
    expect(formatClock(iso)).toBe(clock);
  });
});
