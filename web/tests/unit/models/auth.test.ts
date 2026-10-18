import { describe, expect, it } from "vitest";

import { authSchema } from "@/models/auth";

describe("authSchema", () => {
  it("accepts a valid email and password", () => {
    const result = authSchema.safeParse({
      email: "user@example.com",
      password: "securepass123",
    });
    expect(result.success).toBe(true);
  });

  it("rejects an invalid email format", () => {
    const result = authSchema.safeParse({
      email: "not-an-email",
      password: "securepass123",
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].message).toBe(
      "Please enter a valid email address",
    );
  });

  it("rejects a password shorter than 8 characters", () => {
    const result = authSchema.safeParse({
      email: "user@example.com",
      password: "short",
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].message).toBe(
      "Password must be at least 8 characters long",
    );
  });

  it("rejects a password longer than 72 bytes", () => {
    const result = authSchema.safeParse({
      email: "user@example.com",
      password: "é".repeat(37),
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].message).toBe("Password is too long");
  });

  it("rejects when both fields are missing", () => {
    const result = authSchema.safeParse({});
    expect(result.success).toBe(false);
    expect(result.error?.issues).toHaveLength(2);
  });
});
