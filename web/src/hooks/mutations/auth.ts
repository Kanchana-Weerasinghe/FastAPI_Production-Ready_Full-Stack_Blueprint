import { useMutation, useQueryClient } from "@tanstack/react-query";

import client from "../../lib/client";
import type { AuthInput, MfaSetup, SignInResult } from "../../models/auth";
import { clearAuth } from "../../store/auth.store";

/**
 * Hook for signing in a user.
 * Returns `{ mfaRequired, mfaToken }`: when MFA is enabled no session exists yet and the
 * caller must complete sign-in with `useMfaVerify`. On a full sign-in the profile is refreshed.
 */
export const useSignIn = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: AuthInput): Promise<SignInResult> => {
      const response = await client.post<SignInResult>("/v1/auth/signin", data);
      return response.data;
    },
    onSuccess: (result) => {
      if (!result?.mfaRequired) {
        queryClient.invalidateQueries({ queryKey: ["auth-user"] });
      }
    },
  });
};

/** Completes an MFA sign-in with the challenge token and a TOTP code. */
export const useMfaVerify = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { mfaToken: string; code: string }) => {
      await client.post("/v1/auth/mfa/verify", data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth-user"] });
    },
  });
};

/** Hook for registering a new user. A verification email is sent by the server. */
export const useSignUp = () => {
  return useMutation({
    mutationFn: async (data: AuthInput) => {
      const response = await client.post("/v1/auth/signup", data);
      return response.data;
    },
  });
};

/**
 * Clears local auth state and every cached query, so no user data outlives the session.
 */
const useClearSession = () => {
  const queryClient = useQueryClient();
  return () => {
    clearAuth();
    queryClient.clear();
  };
};

/**
 * Hook for signing out the current user.
 * The server revokes the session and expires the HttpOnly cookies; local state is cleared even if
 * the request fails.
 */
export const useSignOut = () => {
  const clearSession = useClearSession();
  return useMutation({
    mutationFn: async () => {
      await client.post("/v1/auth/signout");
    },
    onSettled: clearSession,
  });
};

/** Revokes every session of the user on all devices. */
export const useSignOutEverywhere = () => {
  const clearSession = useClearSession();
  return useMutation({
    mutationFn: async () => {
      await client.post("/v1/auth/signout-all");
    },
    onSettled: clearSession,
  });
};

/** Requests a password reset email (always succeeds to avoid account enumeration). */
export const useForgotPassword = () =>
  useMutation({
    mutationFn: async (email: string) => {
      await client.post("/v1/auth/password/forgot", { email });
    },
  });

/** Sets a new password using the token from the reset email. */
export const useResetPassword = () =>
  useMutation({
    mutationFn: async (data: { token: string; newPassword: string }) => {
      await client.post("/v1/auth/password/reset", data);
    },
  });

/** Changes the password; the server signs out other sessions and refreshes this one. */
export const useChangePassword = () =>
  useMutation({
    mutationFn: async (data: {
      currentPassword: string;
      newPassword: string;
    }) => {
      await client.post("/v1/auth/password/change", data);
    },
  });

/** Confirms the email address using the token from the verification email. */
export const useVerifyEmail = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (token: string) => {
      await client.post("/v1/auth/verify-email", { token });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["auth-user"] }),
  });
};

/** Sends a new verification email to the signed-in user. */
export const useResendVerification = () =>
  useMutation({
    mutationFn: async () => {
      await client.post("/v1/auth/verify-email/resend");
    },
  });

/** Starts TOTP enrolment: returns the secret and otpauth URI for the authenticator app. */
export const useMfaSetup = () =>
  useMutation({
    mutationFn: async (): Promise<MfaSetup> => {
      const response = await client.post<MfaSetup>("/v1/auth/mfa/setup");
      return response.data;
    },
  });

/** Enables (`enable`) or disables (`disable`) MFA after verifying a TOTP code. */
export const useMfaToggle = (action: "enable" | "disable") => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (code: string) => {
      await client.post(`/v1/auth/mfa/${action}`, { code });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["auth-user"] }),
  });
};
