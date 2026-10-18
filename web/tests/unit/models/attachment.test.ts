import { describe, expect, it } from "vitest";

import { attachmentSchema } from "@/models/attachment";

const validAttachment = {
  id: "att-1",
  userId: "user-1",
  fileName: "report.pdf",
  downloadUrl: "/v2/attachments/att-1:download",
  fileSize: 204800,
  fileType: "application/pdf",
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-01T00:00:00Z",
};

describe("attachmentSchema", () => {
  it("parses a valid attachment object", () => {
    const result = attachmentSchema.safeParse(validAttachment);
    expect(result.success).toBe(true);
  });

  it("allows todoId to be omitted", () => {
    const result = attachmentSchema.safeParse(validAttachment);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.todoId).toBeUndefined();
    }
  });

  it("rejects a download URL outside the authenticated attachments API", () => {
    const result = attachmentSchema.safeParse({
      ...validAttachment,
      downloadUrl: "/uploads/user-1/report.pdf",
    });
    expect(result.success).toBe(false);
  });

  it("rejects when required fields are missing", () => {
    const result = attachmentSchema.safeParse({ id: "att-1" });
    expect(result.success).toBe(false);
  });
});
