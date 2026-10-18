import type { ReactNode } from "react";

interface AuthCardProps {
  title: string;
  children: ReactNode;
}

/** Centered card layout shared by the public account pages (reset password, verify email, ...). */
export function AuthCard({ title, children }: AuthCardProps) {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-4 bg-brand-100">
      <section
        aria-labelledby="auth-card-title"
        className="w-full max-w-sm p-8 rounded-2xl bg-white shadow-xl flex flex-col gap-5"
      >
        <h1 id="auth-card-title" className="text-2xl font-bold text-brand-600">
          {title}
        </h1>
        {children}
      </section>
    </main>
  );
}
