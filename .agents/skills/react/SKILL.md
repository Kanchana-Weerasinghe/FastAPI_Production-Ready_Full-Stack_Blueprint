---
name: react
description: Guidelines for the React frontend, TanStack ecosystem, and React 19 standards. Use when modifying the UI.
---

# React & TypeScript Frontend Guide

Use this skill when modifying, extending, or refactoring the frontend codebase in `web/`.

---

## 1. Technical Stack

* **Core**: React 19 (compatible with React Compiler) & TypeScript 6.
* **Routing**: TanStack Router (Vite file-based routing plugin).
* **State & Query**: TanStack Query (React Query) for API interactions.
* **Forms**: TanStack Form + Zod validation.
* **Styling**: Tailwind CSS v4 (configured via `@tailwindcss/vite`).
* **Notifications**: Sonner (`toast`).
* **Icons**: Lucide React.

---

## 2. React 19 & TypeScript Best Practices

* **Strict Typing**: Always define TypeScript types/interfaces for component props, API request/response structures, and state.
* **Functional Components**: Write pure functional components.
* **React Compiler**: React Compiler is enabled. Avoid manual optimizations using `useMemo` or `useCallback` for simple variables or handlers unless explicitly required for stability of dependency arrays in deep custom hooks. Let the compiler optimize renders automatically.
* **File Structure**:
  * `src/components/`: Shared UI components (like `common/Button.tsx`, `common/Input.tsx`).
  * `src/features/`: Complex feature-specific components (e.g., `account/AccountSecurity.tsx`).
  * `src/hooks/`: Reusable hooks.
  * `src/routes/`: Route definitions matching TanStack Router conventions.

---

## 3. TanStack Router & Routing

* **Route Definitions**: Located under `src/routes/`. Defined via `createFileRoute`.
* **Navigation**:
  * Use `<Link to="...">` for declarative navigation to support type-safe routes.
  * Use `useNavigate` for programmatic navigation:

    ```typescript
    const navigate = useNavigate();
    navigate({ to: "/home" });
    ```

* **Route Trees**: The route tree is automatically generated under `src/routeTree.gen.ts`. Never edit this file manually.

---

## 4. Data Fetching & Mutations (TanStack Query)

* **Isolation**: Keep query and mutation hooks separate from component logic.
  * Queries belong in `src/hooks/queries/`.
  * Mutations belong in `src/hooks/mutations/`.
* **Invalidation**: Always invalidate the query cache on mutation success to keep the UI in sync:

    ```typescript
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: async (data) => {
        await client.post("/v1/auth/mfa/enable", data);
      },
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["auth-user"] });
      },
    });
    ```

---

## 5. Forms & Schema Validation (TanStack Form + Zod)

* **Setup**: Use `useForm` from `@tanstack/react-form` combined with a Zod schema from `src/models/`.
* **Form Submission**:

    ```typescript
    const form = useForm({
      defaultValues: { email: "", password: "" },
      onSubmit: async ({ value }) => {
        await signIn.mutateAsync(value);
      },
    });
    ```

* **Inputs & Fields**: Bind fields using `form.Field` and display validation errors safely:

    ```tsx
    <form.Field
      name="email"
      validators={{
        onChange: authSchema.shape.email,
      }}
      children={(field) => (
        <Input
          value={field.state.value}
          onChange={(e) => field.handleChange(e.target.value)}
          error={field.state.meta.errors.join(", ")}
        />
      )}
    />
    ```

---

## 6. Styling & UI Design

* **Tailwind CSS v4**: Use standard utility classes. Customize styling themes through the global CSS variables.
* **Animations**: Apply micro-interactions and transitions (e.g. `transition-all`, `animate-fade-in-up`, `hover:shadow-lg`) to improve visual feedback.
* **Toasts**: Handle operational successes and failures uniformly using Sonner's `toast.success` and `toast.error`.

---

## Production conventions (see docs/adr/0014-frontend.md)

- **API calls** only through `src/lib/client.ts` (cookies, CSRF header, silent refresh). Never store tokens in `localStorage`/`sessionStorage`.
- **Errors**: show `problemMessage(error, fallback)` from `src/lib/problem.ts`; branch on `getProblem(error)?.code`, never on message text.
- **API types**: use the generated `src/lib/api-types.gen.ts` (`pnpm gen:api` after backend contract changes) instead of hand-writing response types.
- **Accessibility**: every input has a label (the shared `Input` wires `htmlFor`), interactive elements are buttons/links, icon-only buttons have `aria-label`, pages have one `<main>` and a heading. `pnpm lint` enforces `jsx-a11y`.
- **Security**: no inline `<script>`/event-handler strings, no `dangerouslySetInnerHTML` with untrusted data; new external origins must be added to the CSP in `web/nginx.conf`.
