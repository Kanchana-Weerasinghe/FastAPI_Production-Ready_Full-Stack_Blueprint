import { describe, expect, it } from "vitest";

import { Route as RootRoute } from "@/routes/__root";
import { Route as AccountRoute } from "@/routes/_authenticated/account";
import { Route as HomeRoute } from "@/routes/_authenticated/home";
import { Route as GuestIndexRoute } from "@/routes/_guest/index";

describe("Route Configurations", () => {
  it("exports valid route definitions", () => {
    expect(RootRoute).toBeDefined();
    expect(RootRoute.options.component).toBeDefined();

    expect(HomeRoute).toBeDefined();
    expect(HomeRoute.options.component).toBeDefined();

    expect(AccountRoute).toBeDefined();
    expect(AccountRoute.options.component).toBeDefined();

    expect(GuestIndexRoute).toBeDefined();
    expect(GuestIndexRoute.options.component).toBeDefined();
  });
});
