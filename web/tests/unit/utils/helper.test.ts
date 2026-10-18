import { describe, expect, it, vi } from "vitest";

import {
  formatDate,
  formatFileSize,
  getDownloadUrl,
  getErrorMessage,
  MAX_FILE_SIZE,
  validateFileSize,
} from "@/utils/helper";

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

describe("formatFileSize", () => {
  it("returns '0 Bytes' for 0", () => {
    expect(formatFileSize(0)).toBe("0 Bytes");
  });

  it("formats bytes correctly", () => {
    expect(formatFileSize(512)).toBe("512 Bytes");
  });

  it("formats kilobytes correctly", () => {
    expect(formatFileSize(1024)).toBe("1 KB");
  });

  it("formats megabytes correctly", () => {
    expect(formatFileSize(1048576)).toBe("1 MB");
  });
});

describe("validateFileSize", () => {
  it("returns true for a file within the size limit", () => {
    const file = { size: 1024 } as File;
    expect(validateFileSize(file)).toBe(true);
  });

  it("returns true for a file exactly at the size limit", () => {
    const file = { size: MAX_FILE_SIZE } as File;
    expect(validateFileSize(file)).toBe(true);
  });

  it("returns false for a file exceeding the size limit", () => {
    const file = { size: MAX_FILE_SIZE + 1 } as File;
    expect(validateFileSize(file)).toBe(false);
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

describe("getDownloadUrl", () => {
  it("returns a URL using the VITE_API_URL env variable", () => {
    vi.stubEnv("VITE_API_URL", "http://api.example.com");
    const url = getDownloadUrl("file-123");
    expect(url).toBe("http://api.example.com/v2/attachments/file-123:download");
    vi.unstubAllEnvs();
  });

  it("uses the same origin when VITE_API_URL is set but empty", () => {
    vi.stubEnv("VITE_API_URL", "");
    const url = getDownloadUrl("file-456");
    expect(url).toBe("/v2/attachments/file-456:download");
    vi.unstubAllEnvs();
  });
});
