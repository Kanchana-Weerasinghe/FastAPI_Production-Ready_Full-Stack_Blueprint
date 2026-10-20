import { describe, expect, it } from "vitest";

import { formatDate, getErrorMessage } from "@/utils/helper";

describe("getErrorMessage", () => {
  it("returns the string directly if error is a string", () => {
    expect(getErrorMessage("something went wrong")).toBe(
      "something went wrong",
    );
  });

  it("extracts message from an Error object", () => {
    expect(getErrorMessage(new Error("network failure"))).toBe(
      "network failure",
    );
  });

  it("returns undefined for null or unrecognized types", () => {
    expect(getErrorMessage(null)).toBeUndefined();
    expect(getErrorMessage(42)).toBeUndefined();
  });
});

describe("formatDate", () => {
  it("formats an ISO string into the expected format", () => {
    const result = formatDate("2024-05-10T14:30:00Z");
    expect(result).toMatch(/May \d+ 2024, \d+:\d{2} (AM|PM)/);
  });

  it("accepts a Date object", () => {
    const result = formatDate(new Date("2024-01-01T09:00:00Z"));
    expect(result).toMatch(/January \d+ 2024, \d+:\d{2} (AM|PM)/);
  });
});
