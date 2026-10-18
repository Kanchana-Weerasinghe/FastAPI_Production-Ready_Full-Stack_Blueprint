import { z } from "zod";

/**
 * Zod schema for the User profile.
 * Validates core identity fields for the authenticated session.
 */
export const userSchema = z.object({
  id: z.string(),
  email: z.email(),
  username: z.string(),
  role: z.string().default("user"),
  emailVerified: z.boolean().default(false),
  mfaEnabled: z.boolean().default(false),
});

export type User = z.infer<typeof userSchema>;
