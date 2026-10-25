import { Link, useLocation, useNavigate } from "@tanstack/react-router";
import { LogOut } from "lucide-react";
import { useEffect, useRef } from "react";

import { NAV_ITEMS } from "../../constants/navbar.constants";
import { useSignOut } from "../../hooks/mutations/auth";

let lastIndicatorStyle = { left: 0, width: 0 };

/**
 * The primary navigation bar of the application.
 * Features a dynamic active item indicator with smooth sliding animations.
 */
export function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const signOut = useSignOut();
  const isAnyActive = NAV_ITEMS.some((item) =>
    location.pathname.startsWith(item.to),
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const indicatorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      setTimeout(() => {
        const activeLink = containerRef.current?.querySelector(
          ".active",
        ) as HTMLElement;
        if (activeLink && indicatorRef.current) {
          const newStyle = {
            left: activeLink.offsetLeft,
            width: activeLink.offsetWidth,
          };
          indicatorRef.current.style.opacity = "1";
          indicatorRef.current.style.left = `${newStyle.left}px`;
          indicatorRef.current.style.width = `${newStyle.width}px`;
          lastIndicatorStyle = newStyle;
        } else if (indicatorRef.current) {
          indicatorRef.current.style.opacity = "0";
          indicatorRef.current.style.width = "0px";
        }
      }, 50);
    }
  }, [location.pathname]);

  return (
    <nav className="bg-brand-100">
      <div className="max-w-5xl mx-auto px-10 py-8 flex items-center justify-between">
        <Link
          to="/"
          className="pt-3 text-4xl font-borel font-bold text-brand-400 select-none hover:opacity-90 transition-opacity"
        >
          Boost
        </Link>

        <div className="relative" ref={containerRef}>
          <div className="flex gap-12 items-center">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="text-xl font-bold text-gray-700 hover:text-brand-400 transition-colors py-2 px-1 relative z-10 [&.active]:text-brand-400"
              >
                {item.label}
              </Link>
            ))}
          </div>

          <div
            ref={indicatorRef}
            className={`absolute bottom-0 h-1 bg-brand-400 rounded-full transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] animate-in fade-in ${
              !isAnyActive ? "opacity-0 w-0" : ""
            }`}
            style={{
              left: lastIndicatorStyle.left,
              width: isAnyActive ? lastIndicatorStyle.width : 0,
            }}
          />
        </div>

        <button
          type="button"
          aria-label="Sign out"
          title="Sign out"
          disabled={signOut.isPending}
          onClick={() =>
            signOut.mutate(undefined, {
              onSettled: () => navigate({ to: "/" }),
            })
          }
          className="p-2 text-gray-700 hover:text-brand-400 transition-colors disabled:opacity-50 cursor-pointer"
        >
          <LogOut className="w-6 h-6" />
        </button>
      </div>
    </nav>
  );
}
