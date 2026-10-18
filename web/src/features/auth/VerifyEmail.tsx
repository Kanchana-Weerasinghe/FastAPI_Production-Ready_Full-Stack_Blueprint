import { Link } from "@tanstack/react-router";
import { useEffect } from "react";

import { AuthCard } from "../../components/AuthCard";
import { useVerifyEmail } from "../../hooks/mutations/auth";
import { problemMessage } from "../../lib/problem";

/** Confirms the email address with the token from the verification link, once, on page load. */
export function VerifyEmail({ token }: { token?: string }) {
  const verify = useVerifyEmail();
  const { mutate } = verify;

  useEffect(() => {
    if (token) mutate(token);
  }, [token, mutate]);

  return (
    <AuthCard title="Email verification">
      <p role="status" className="text-gray-700">
        {!token
          ? "This verification link is incomplete."
          : verify.isPending || verify.isIdle
            ? "Verifying your email address..."
            : verify.isSuccess
              ? "Your email address is verified. Thank you!"
              : problemMessage(
                  verify.error,
                  "This link is invalid or has expired.",
                )}
      </p>
      <Link to="/" className="text-sm font-bold text-brand-400 hover:underline">
        Continue
      </Link>
    </AuthCard>
  );
}
