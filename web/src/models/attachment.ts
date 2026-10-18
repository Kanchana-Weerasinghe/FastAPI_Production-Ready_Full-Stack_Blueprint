import { z } from "zod";

/**
 * Zod schema for file attachment metadata.
 * Validates fields returned from the V2 Attachment API.
 */
export const attachmentSchema = z.object({
  id: z.string(),
  userId: z.string(),
  todoId: z.string().optional(),
  fileName: z.string(),
  // Authenticated, ownership-checked download path (files are never publicly served).
  downloadUrl: z.string().startsWith("/v2/attachments/"),
  fileSize: z.number(),
  fileType: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export type Attachment = z.infer<typeof attachmentSchema>;

export interface AttachmentListResponse {
  founds: Attachment[];
  searchOptions: {
    totalCount: number;
    pageSize: number;
    currentPage: number;
  };
}
