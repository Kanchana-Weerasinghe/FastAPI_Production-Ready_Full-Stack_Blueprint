import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";

import { AuthCard } from "../../components/AuthCard";
import { Button } from "../../components/common/Button";
import { Input } from "../../components/common/Input";
import { useResetPassword } from "../../hooks/mutations/auth";
import { problemMessage } from "../../lib/problem";
import { newPasswordSchema } from "../../models/auth";

/** Sets a new password from the single-use token in the reset email. */
export function ResetPassword({ token }: { token?: string }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string>();
  const reset = useResetPassword();
  const navigate = useNavigate();

  if (!token) {
    return (
      <AuthCard title="Invalid link">
        <p className="text-gray-700">This reset link is incomplete.</p>
        <Link
          to="/forgot-password"
          className="font-bold text-brand-400 hover:underline"
        >
          Request a new link
        </Link>
      </AuthCard>
    );
  }

  const submit = async () => {
    const parsed = newPasswordSchema.safeParse(password);
    if (!parsed.success) {
      setError(parsed.error.issues[0].message);
      return;
    }
    try {
      await reset.mutateAsync({ token, newPassword: password });
      toast.success("Password changed", {
        description: "Sign in with your new password.",
      });
      navigate({ to: "/" });
    } catch (e) {
      setError(problemMessage(e, "Could not reset the password."));
    }
  };

  return (
    <AuthCard title="Choose a new password">
      <form
        className="flex flex-col gap-5"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <Input
          label="New password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            setError(undefined);
          }}
          error={error}
        />
        <Button type="submit" disabled={reset.isPending}>
          {reset.isPending ? "Saving..." : "Set new password"}
        </Button>
      </form>
    </AuthCard>
  );
}
