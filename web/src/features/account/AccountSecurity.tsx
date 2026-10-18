import { useNavigate } from "@tanstack/react-router";
import { type ReactNode, useState } from "react";
import { toast } from "sonner";

import { Button } from "../../components/common/Button";
import { Input } from "../../components/common/Input";
import {
  useChangePassword,
  useMfaSetup,
  useMfaToggle,
  useResendVerification,
  useSignOutEverywhere,
} from "../../hooks/mutations/auth";
import { useUser } from "../../hooks/queries/user";
import { problemMessage } from "../../lib/problem";
import { newPasswordSchema, totpCodeSchema } from "../../models/auth";

function Section({ title, children }: { title: string; children: ReactNode }) {
  const id = `section-${title.toLowerCase().replace(/\W+/g, "-")}`;
  return (
    <section
      aria-labelledby={id}
      className="bg-white rounded-2xl shadow p-6 flex flex-col gap-4"
    >
      <h2 id={id} className="text-xl font-bold text-brand-600">
        {title}
      </h2>
      {children}
    </section>
  );
}

/**
 * Account security settings: email verification, password change, TOTP MFA and
 * signing out of every device.
 */
export function AccountSecurity() {
  const { data: user } = useUser();
  const navigate = useNavigate();

  const resend = useResendVerification();
  const changePassword = useChangePassword();
  const mfaSetup = useMfaSetup();
  const mfaEnable = useMfaToggle("enable");
  const mfaDisable = useMfaToggle("disable");
  const signOutEverywhere = useSignOutEverywhere();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string>();
  const [mfaCode, setMfaCode] = useState("");
  const [mfaError, setMfaError] = useState<string>();

  const submitPassword = async () => {
    const parsed = newPasswordSchema.safeParse(newPassword);
    if (!parsed.success) {
      setPasswordError(parsed.error.issues[0].message);
      return;
    }
    try {
      await changePassword.mutateAsync({ currentPassword, newPassword });
      setCurrentPassword("");
      setNewPassword("");
      toast.success("Password changed", {
        description: "Other devices were signed out.",
      });
    } catch (e) {
      setPasswordError(problemMessage(e, "Could not change the password."));
    }
  };

  const submitMfa = async (action: "enable" | "disable") => {
    const parsed = totpCodeSchema.safeParse(mfaCode);
    if (!parsed.success) {
      setMfaError(parsed.error.issues[0].message);
      return;
    }
    try {
      await (action === "enable" ? mfaEnable : mfaDisable).mutateAsync(mfaCode);
      setMfaCode("");
      mfaSetup.reset();
      toast.success(
        action === "enable"
          ? "Two-factor authentication enabled"
          : "Two-factor authentication disabled",
      );
    } catch (e) {
      setMfaError(problemMessage(e, "Invalid authentication code"));
    }
  };

  const mfaCodeInput = (
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
    />
  );

  return (
    <main className="max-w-2xl w-full mx-auto px-6 pb-16 flex flex-col gap-6">
      <h1 className="text-3xl font-bold text-brand-600">Account security</h1>

      <Section title="Email">
        <p className="text-gray-700">
          {user?.email} —{" "}
          <strong>{user?.emailVerified ? "verified" : "not verified"}</strong>
        </p>
        {user && !user.emailVerified && (
          <Button
            variant="outline"
            disabled={resend.isPending || resend.isSuccess}
            onClick={() => resend.mutate()}
          >
            {resend.isSuccess
              ? "Verification email sent"
              : "Resend verification email"}
          </Button>
        )}
      </Section>

      <Section title="Password">
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            submitPassword();
          }}
        >
          <Input
            label="Current password"
            type="password"
            autoComplete="current-password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
          />
          <Input
            label="New password"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => {
              setNewPassword(e.target.value);
              setPasswordError(undefined);
            }}
            error={passwordError}
          />
          <Button
            type="submit"
            disabled={changePassword.isPending || !currentPassword}
          >
            Change password
          </Button>
        </form>
      </Section>

      <Section title="Two-factor authentication">
        {user?.mfaEnabled ? (
          <form
            className="flex flex-col gap-4"
            noValidate
            onSubmit={(e) => {
              e.preventDefault();
              submitMfa("disable");
            }}
          >
            <p className="text-gray-700">
              Enabled. Enter a current code to turn it off.
            </p>
            {mfaCodeInput}
            <Button
              type="submit"
              variant="outline"
              disabled={mfaDisable.isPending}
            >
              Disable two-factor authentication
            </Button>
          </form>
        ) : mfaSetup.data ? (
          <form
            className="flex flex-col gap-4"
            noValidate
            onSubmit={(e) => {
              e.preventDefault();
              submitMfa("enable");
            }}
          >
            <p className="text-gray-700">
              Add this account to your authenticator app (
              <a
                className="font-bold text-brand-400 underline"
                href={mfaSetup.data.otpauthUri}
              >
                open in app
              </a>{" "}
              or enter the key manually), then type the 6-digit code it shows.
            </p>
            <code className="break-all bg-brand-100 rounded p-2 text-sm">
              {mfaSetup.data.secret}
            </code>
            {mfaCodeInput}
            <Button type="submit" disabled={mfaEnable.isPending}>
              Enable two-factor authentication
            </Button>
          </form>
        ) : (
          <>
            <p className="text-gray-700">
              Protect your account with a code from an authenticator app.
            </p>
            <Button
              disabled={mfaSetup.isPending}
              onClick={() =>
                mfaSetup.mutate(undefined, {
                  onError: (e) =>
                    toast.error(problemMessage(e, "Could not start setup")),
                })
              }
            >
              Set up two-factor authentication
            </Button>
          </>
        )}
      </Section>

      <Section title="Sessions">
        <p className="text-gray-700">
          Signed in on a device you don&apos;t recognise? Sign out everywhere,
          including here.
        </p>
        <Button
          variant="outline"
          disabled={signOutEverywhere.isPending}
          onClick={() =>
            signOutEverywhere.mutate(undefined, {
              onSettled: () => navigate({ to: "/" }),
            })
          }
        >
          Sign out of all devices
        </Button>
      </Section>
    </main>
  );
}
