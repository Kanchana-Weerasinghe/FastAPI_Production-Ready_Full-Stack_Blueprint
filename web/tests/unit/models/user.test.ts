import { describe, expect, it } from "vitest";

import { userSchema } from "@/models/user";

describe("userSchema", () => {
  it("parses a valid user object", () => {
    const result = userSchema.safeParse({
      id: "user-uuid-1",
      email: "user@example.com",
      username: "john_doe",
    });
    expect(result.success).toBe(true);
  });

  it("rejects an invalid email", () => {
    const result = userSchema.safeParse({
      id: "user-uuid-1",
      email: "bad-email",
      username: "john_doe",
    });
    expect(result.success).toBe(false);
  });

  it("rejects when required fields are missing", () => {
    const result = userSchema.safeParse({ id: "user-uuid-1" });
    expect(result.success).toBe(false);
  });
});
