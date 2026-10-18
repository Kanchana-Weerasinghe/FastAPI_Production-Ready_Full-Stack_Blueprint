import { Link } from "@tanstack/react-router";
import { useState } from "react";

import { AuthCard } from "../../components/AuthCard";
import { Button } from "../../components/common/Button";
import { Input } from "../../components/common/Input";
import { useForgotPassword } from "../../hooks/mutations/auth";
import { problemMessage } from "../../lib/problem";
import { authSchema } from "../../models/auth";

/**
 * Requests a password reset link. The API answers the same way whether or not the account exists,
 * so the page always shows the same confirmation.
 */
export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string>();
  const forgot = useForgotPassword();

  const submit = async () => {
    const parsed = authSchema.shape.email.safeParse(email);
    if (!parsed.success) {
      setError(parsed.error.issues[0].message);
      return;
    }
    try {
      await forgot.mutateAsync(email);
    } catch (e) {
      setError(problemMessage(e, "Could not send the email. Try again later."));
    }
  };

  return (
    <AuthCard title="Reset your password">
      {forgot.isSuccess ? (
        <p role="status" className="text-gray-700">
          If an account exists for {email}, we sent a link to reset the
          password. It expires soon and can be used once.
        </p>
      ) : (
        <form
          className="flex flex-col gap-5"
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setError(undefined);
            }}
            error={error}
          />
          <Button type="submit" disabled={forgot.isPending}>
            {forgot.isPending ? "Sending..." : "Send reset link"}
          </Button>
        </form>
      )}
      <Link to="/" className="text-sm font-bold text-brand-400 hover:underline">
        Back to sign in
      </Link>
    </AuthCard>
  );
}
