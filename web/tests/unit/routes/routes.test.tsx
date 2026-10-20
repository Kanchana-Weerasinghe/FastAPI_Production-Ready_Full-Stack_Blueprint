import { describe, expect, it } from "vitest";

import { Route as RootRoute } from "@/routes/__root";
import { Route as ArchivesRoute } from "@/routes/_authenticated/archives";
import { Route as TodoEditRoute } from "@/routes/_authenticated/todo/$todoId/edit";
import { Route as TodoIndexRoute } from "@/routes/_authenticated/todo/$todoId/index";
import { Route as TodoNewRoute } from "@/routes/_authenticated/todo/new";
import { Route as TodosIndexRoute } from "@/routes/_authenticated/todos/index";
import { Route as GuestIndexRoute } from "@/routes/_guest/index";

describe("Route Configurations", () => {
  it("exports valid route definitions", () => {
    expect(RootRoute).toBeDefined();
    expect(RootRoute.options.component).toBeDefined();

    expect(ArchivesRoute).toBeDefined();
    expect(ArchivesRoute.options.component).toBeDefined();

    expect(TodoEditRoute).toBeDefined();
    expect(TodoEditRoute.options.component).toBeDefined();

    expect(TodoIndexRoute).toBeDefined();
    expect(TodoIndexRoute.options.component).toBeDefined();

    expect(TodoNewRoute).toBeDefined();
    expect(TodoNewRoute.options.component).toBeDefined();

    expect(TodosIndexRoute).toBeDefined();
    expect(TodosIndexRoute.options.component).toBeDefined();

    expect(GuestIndexRoute).toBeDefined();
    expect(GuestIndexRoute.options.component).toBeDefined();
  });
});
