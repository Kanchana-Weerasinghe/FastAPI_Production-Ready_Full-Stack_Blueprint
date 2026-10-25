import { Link } from "@tanstack/react-router";
import { BookOpen, Braces, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

import { GUIDE_URL } from "../constants/guide.constants";
import { useUser } from "../hooks/queries/user";
import { apiBaseUrl } from "../lib/config";

function Tile({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="bg-white rounded-2xl shadow p-6 flex flex-col gap-3">
      <div className="flex items-center gap-3 text-brand-600">
        {icon}
        <h2 className="text-xl font-bold">{title}</h2>
      </div>
      {children}
    </div>
  );
}

const linkClass = "font-bold text-brand-400 hover:underline";

/**
 * The signed-in starting page of the template.
 * Replace it with the first screen of your application.
 */
export function Home() {
  const { data: user } = useUser();

  return (
    <main className="max-w-5xl w-full mx-auto px-10 pb-16 flex flex-col gap-8">
      <header>
        <h1 className="text-3xl font-bold text-brand-600">Welcome to Boost</h1>
        {user && (
          <p className="text-gray-700 mt-2">Signed in as {user.email}</p>
        )}
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <Tile icon={<BookOpen className="w-6 h-6" />} title="Boost Guide">
          <p className="text-gray-700">
            Architecture, the delivery process, and how to generate tests and
            code for a new entity.
          </p>
          <a href={GUIDE_URL} className={linkClass}>
            Open the guide
          </a>
          <a href={`${GUIDE_URL}#quick-start`} className={linkClass}>
            Quick start · build your first entity
          </a>
        </Tile>

        <Tile icon={<ShieldCheck className="w-6 h-6" />} title="Your account">
          <p className="text-gray-700">
            Email verification, password, two-factor authentication and
            sessions.
          </p>
          <Link to="/account" className={linkClass}>
            Account security
          </Link>
        </Tile>

        {import.meta.env.DEV && (
          <Tile icon={<Braces className="w-6 h-6" />} title="API reference">
            <p className="text-gray-700">
              Try every endpoint in Swagger UI (development only).
            </p>
            <a href={`${apiBaseUrl()}/docs`} className={linkClass}>
              Open Swagger UI
            </a>
          </Tile>
        )}
      </div>
    </main>
  );
}
