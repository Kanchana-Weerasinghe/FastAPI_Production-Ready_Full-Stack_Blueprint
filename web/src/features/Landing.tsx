import { useForm } from "@tanstack/react-form";
import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "../components/common/Button";
import { Input } from "../components/common/Input";
import { useMfaVerify, useSignIn, useSignUp } from "../hooks/mutations/auth";
import { problemMessage } from "../lib/problem";
import { authSchema, totpCodeSchema } from "../models/auth";
import { getErrorMessage } from "../utils/helper";

/**
 * The Landing/Authentication feature page.
 * Handles both Sign In and Sign Up flows using a shared form,
 * with validation provided by TanStack Form and Zod.
 */
export function Landing() {
  const [isSignIn, setIsSignIn] = useState(true);
  const navigate = useNavigate();

  const signIn = useSignIn();
  const signUp = useSignUp();
  const mfaVerify = useMfaVerify();
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState("");
  const [mfaError, setMfaError] = useState<string | undefined>();

  const form = useForm({
    defaultValues: {
      email: "",
      password: "",
    },
    onSubmit: async ({ value }) => {
      try {
        if (isSignIn) {
          const result = await signIn.mutateAsync(value);
          if (result.mfaRequired && result.mfaToken) {
            setMfaToken(result.mfaToken);
            return;
          }
          toast.success("Welcome back!", {
            description: `Logged in as ${value.email}`,
          });
          navigate({ to: "/todos" });
        } else {
          await signUp.mutateAsync(value);
          toast.success("Account created!", {
            description: "Check your inbox to verify your email, then sign in.",
          });
          setIsSignIn(true);
        }
      } catch (error) {
        toast.error("Authentication failed", {
          description: problemMessage(error, "Something went wrong"),
        });
      }
    },
  });

  const handleModeSwitch = (signIn: boolean) => {
    setIsSignIn(signIn);
    form.reset();
  };

  const submitMfaCode = async () => {
    const parsed = totpCodeSchema.safeParse(mfaCode);
    if (!parsed.success) {
      setMfaError(parsed.error.issues[0].message);
      return;
    }
    try {
      await mfaVerify.mutateAsync({ mfaToken: mfaToken!, code: mfaCode });
      navigate({ to: "/todos" });
    } catch (error) {
      setMfaError(problemMessage(error, "Invalid authentication code"));
    }
  };

  if (mfaToken) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center p-4 bg-brand-100">
        <form
          className="w-full max-w-sm p-8 rounded-2xl bg-white shadow-xl flex flex-col gap-5"
          onSubmit={(e) => {
            e.preventDefault();
            submitMfaCode();
          }}
          noValidate
        >
          <h1 className="text-2xl font-bold text-brand-600">
            Two-factor authentication
          </h1>
          <p className="text-gray-700">
            Enter the 6-digit code from your authenticator app.
          </p>
          <Input
            label="Authentication code"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={mfaCode}
            onChange={(e) => {
              setMfaCode(e.target.value.trim());
              setMfaError(undefined);
            }}
            error={mfaError}
            // eslint-disable-next-line jsx-a11y/no-autofocus -- single-field step the user just navigated to
            autoFocus
          />
          <Button type="submit" disabled={mfaVerify.isPending}>
            {mfaVerify.isPending ? "Verifying..." : "Verify"}
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setMfaToken(null);
              setMfaCode("");
            }}
          >
            Back to sign in
          </Button>
        </form>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-4 bg-brand-100">
      <div className="w-full max-w-sm p-8 rounded-2xl bg-white shadow-xl">
        <div className="text-center mb-8 pt-6">
          <h1 className="text-4xl font-borel font-bold text-brand-400 mb-1 py-1">
            Tempto
          </h1>
          <p className="text-base font-borel text-brand-600/80">
            Your everyday todo app.
          </p>
        </div>

        <div className="flex mb-8 border-b-2 border-brand-200/50 relative">
          <Button
            type="button"
            variant="ghost"
            className={`flex-1 py-3 text-lg active:scale-100 ${isSignIn ? "text-brand-400" : "text-gray-700 hover:text-brand-400"}`}
            onClick={() => handleModeSwitch(true)}
          >
            Sign in
          </Button>
          <Button
            type="button"
            variant="ghost"
            className={`flex-1 py-3 text-lg active:scale-100 ${!isSignIn ? "text-brand-400" : "text-gray-700 hover:text-brand-400"}`}
            onClick={() => handleModeSwitch(false)}
          >
            Sign up
          </Button>
          <div
            className={`absolute bottom-0 h-1 bg-brand-400 rounded-full transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] ${isSignIn ? "left-0 w-1/2" : "left-1/2 w-1/2"}`}
          />
        </div>

        <form
          className="flex flex-col gap-5"
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            form.handleSubmit();
          }}
          noValidate
        >
          <form.Field
            name="email"
            validators={{
              onChangeAsync: authSchema.shape.email,
              onChangeAsyncDebounceMs: 300,
            }}
          >
            {(field) => (
              <Input
                label="Email"
                type="email"
                placeholder="you@example.com"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => field.handleChange(e.target.value)}
                error={
                  !field.state.meta.isValidating
                    ? getErrorMessage(field.state.meta.errors[0])
                    : undefined
                }
              />
            )}
          </form.Field>

          <form.Field
            name="password"
            validators={{
              onChangeAsync: authSchema.shape.password,
              onChangeAsyncDebounceMs: 300,
            }}
          >
            {(field) => (
              <Input
                label="Password"
                type="password"
                placeholder="••••••••"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => field.handleChange(e.target.value)}
                error={
                  !field.state.meta.isValidating
                    ? getErrorMessage(field.state.meta.errors[0])
                    : undefined
                }
              />
            )}
          </form.Field>

          <form.Subscribe
            selector={(state) => [state.canSubmit, state.isSubmitting]}
          >
            {([canSubmit, isSubmitting]) => (
              <Button
                type="submit"
                disabled={!canSubmit}
                className="mt-2 w-full py-4 rounded-xl shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting
                  ? "Processing..."
                  : isSignIn
                    ? "Sign in"
                    : "Sign up"}
              </Button>
            )}
          </form.Subscribe>
          {isSignIn && (
            <Link
              to="/forgot-password"
              className="text-sm font-bold text-brand-400 hover:underline text-center"
            >
              Forgot your password?
            </Link>
          )}
        </form>
      </div>
    </main>
  );
}
