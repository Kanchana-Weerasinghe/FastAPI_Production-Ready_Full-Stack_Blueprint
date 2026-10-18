import { z } from "zod";

/** bcrypt only uses the first 72 bytes of a password; the backend rejects anything longer. */
const BCRYPT_MAX_BYTES = 72;

/**
 * Zod schema for authentication inputs (Sign In / Sign Up).
 * Mirrors the backend policy: valid email, 8 characters minimum, 72 bytes maximum.
 */
export const authSchema = z.object({
  email: z.email("Please enter a valid email address"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters long")
    .refine(
      (value) => new TextEncoder().encode(value).length <= BCRYPT_MAX_BYTES,
      "Password is too long",
    ),
});

export type AuthInput = z.infer<typeof authSchema>;

/** Response of POST /v1/auth/signin: either a session (cookies) or an MFA challenge. */
export interface SignInResult {
  mfaRequired: boolean;
  mfaToken: string | null;
}

/** 6-digit TOTP code from an authenticator app. */
export const totpCodeSchema = z
  .string()
  .regex(/^\d{6}$/, "Enter the 6-digit code from your authenticator app");

export const newPasswordSchema = authSchema.shape.password;

export interface MfaSetup {
  secret: string;
  otpauthUri: string;
}
