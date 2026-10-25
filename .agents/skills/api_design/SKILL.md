---
name: api-design
description: Guidelines for RESTful API design, endpoint naming conventions, and standardizing JSON responses.
---

# API Design Guide

## Overview

This skill captures the principles and rules of RESTful API design. Apply it whenever designing, reviewing, generating, or evaluating APIs in the codebase.

---

## 1. Core Philosophy: Resource-Oriented Design

APIs **must** be designed around **resources** (nouns), not actions (verbs).

**Key principles:**

- Model the API as a resource hierarchy — collections containing resources of the same type.
- Expose a **large number of resources** with a **small number of methods** on each.
- Use a **stateless protocol**: every request is independent; the server persists data, the client manages application state.
- Resource relationships **must** form a directed acyclic graph — no cyclic references.
- An API's resource model **must not** mirror the underlying database schema; that is an anti-pattern.

**Design order (logical sequence):**

1. Identify the resources (nouns) the API provides.
2. Define relationships and hierarchies between resources.
3. Define the schema (fields) of each resource.
4. Assign methods (verbs) to resources, preferring standard methods.

---

## 2. Resource Names

Resource names are **hierarchical, slash-separated paths** in the URL that uniquely identify a resource.

**Format:**

```bash
/{collection}/{resource_id}/{sub-collection}/{sub-resource_id}
```

**Examples:**

```bash
/shelves/shelf1/books/book2
/publishers/publisher1/books/book1
```

**Rules:**

- Collection IDs are **plural** (e.g., `books`, `shelves`) unless the word has no plural form (e.g., `weather`, `evidence`).
- Resource IDs must be URL-safe strings.
- A resource **must** have exactly one canonical parent in the hierarchy.
- Names are used across all methods consistently — the same resource name identifies the same resource everywhere in the API.

---

## 3. Standard Methods

Prefer standard methods over custom methods whenever the operation fits.

| Method | HTTP Mapping | Request Body | Response Body |
| -------- | ------------- | ------------- | --------------- |
| **List** | `GET /{collection}` | None | Contains array of resources |
| **Get** | `GET /{collection}/{resource_id}` | None | Is the resource |
| **Create** | `POST /{collection}` | Contains resource | Is the resource |
| **Update** | `PATCH /{collection}/{resource_id}` | Contains resource | Is the resource |
| **Delete** | `DELETE /{collection}/{resource_id}` | None | None (empty) |

**Mandatory requirements:**

- Every resource **must** support **Get** (clients must be able to validate state after mutations).
- Every resource **must** support **List**, except singleton resources.
- Update **should** use `PATCH` (or field-specific update requests), not `PUT`, to allow partial updates.
- Delete **should** return `404 Not Found` on subsequent Gets after a successful delete.

**Strong consistency:** After a successful Create, Update, or Delete, a subsequent Get **must** reflect the final state.

---

## 4. Custom Methods

Use custom methods only when the operation does **not** cleanly map to a standard method.

**Rules:**

- Custom methods use standard HTTP verbs (usually `POST`).
- The custom verb appears in the URI as a colon-separated suffix: `{resource_uri}:{verb}`.
- Examples: `:cancel`, `:move`, `:search`, `:undelete`, `:batch-get`.

```bash
POST /books/book1:cancel
POST /shelves/shelf1/books:batch-get
```

**When custom methods are appropriate:**

- Database-transaction-like operations (`:commit`, `:rollback`)
- Import/export flows
- Complex data analysis operations
- Undoing a delete (`:undelete`)

---

## 5. Naming & Case Conventions

All API elements **should** be: **simple, intuitive, consistent.**

### General rules

- Use **American English** (e.g., `color` not `colour`, `license` not `licence`).
- Avoid overly generic names: `instance`, `info`, `service` are often too vague — be specific.
- Use the **same name** for the same concept across all APIs.
- Do **not** overload names — different concepts get different names.
- Avoid names that conflict with keywords in common programming languages.

### Naming Case Alignment (Frontend/Backend Compatibility)

- **Request Bodies**: The API **must** support both **JavaScript naming convention** (`camelCase`) and **Python naming convention** (`snake_case`) in JSON requests. This provides maximum developer convenience.
- **Response Bodies**: When sending response payloads to the frontend, they **must** be serialized using the **JavaScript naming convention** (`camelCase`).

### Field names

- Timestamps: use `created_at`, `updated_at`, `deleted_at` (serialized to `createdAt`, `updatedAt`, `deletedAt` in responses).
- Quantities: name indicating the property (e.g., `file_size` in bytes).
- Booleans: prefix with `is_` to indicate a state or condition (e.g., `is_completed`, `is_active`, which serialize to `isCompleted`, `isActive` in responses).

---

## 6. Standard Fields

Commonly needed fields **must** use these standard names and types:

| Field (JSON/camelCase) | Type | Description |
| -------- | -------- | -------- |
| `id` | `string` (UUID) | Unique identifier |
| `createdAt` | `string` (ISO-8601 DateTime) | When the resource was created |
| `updatedAt` | `string` (ISO-8601 DateTime) | When the resource was last updated |
| `deletedAt` | `string` (ISO-8601 DateTime) | When the resource was soft-deleted |
| `isActive` | `boolean` | Whether the resource is active (not archived) |
| `createdBy` | `string` | Username of the creator |
| `updatedBy` | `string` | Username of the last updater |
| `page` | `integer` | Page number to retrieve |
| `pageSize` | `integer` | Max results per page |
| `totalCount` | `integer` | Total number of items matching query |
| `ordering` | `string` | Sort order for List |

---

## 7. Errors

**All** API errors **must** be [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) Problem Details (`application/problem+json`) with a canonical HTTP status code. Never build error JSON by hand: raise a domain error from `app/core/errors.py` (optionally with a specific `code=`) and the handlers in `app/core/error_handlers.py` render it. See `docs/adr/0002-rfc9457-error-format.md`.

### Error structure (General)

```json
{
  "type": "https://errors.example.com/project_not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Project with ID 'shelf1' not found.",
  "instance": "/v2/projects/shelf1",
  "code": "project_not_found",
  "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a"
}
```

### Error structure (Validation Error)

```json
{
  "type": "https://errors.example.com/validation_failed",
  "title": "Validation Failed",
  "status": 422,
  "detail": "Input validation failed.",
  "instance": "/v2/projects/",
  "code": "validation_failed",
  "request_id": "8c1b2f0e-5d7a-4c1e-9f3b-2a6d4e8c0b1a",
  "errors": [
    {
      "field": "title",
      "message": "Field required",
      "type": "missing"
    }
  ]
}
```

### Rules

- `code` is a **stable contract**: clients branch on it, so never rename a published code; add new ones instead.
- The `detail` must be **developer-facing**, **human-readable**, and **in English**.
- Messages must be **brief and actionable** — describe the problem and suggest a resolution.
- Messages **must not** expose internal implementation details.
- For unauthorized access: do **not** reveal whether the resource exists; use a generic message.

---

## 8. Versioning

APIs support URL-based major versions:

```bash
/v1/shelves
/v2/shelves
```

**Breaking change rules:**

- Never make breaking changes within a stable major version (`v1`, `v2`).
- Breaking changes require a major version increment.

**What counts as a breaking change:**

- Removing or renaming a field, method, or resource
- Changing a field's type
- Changing HTTP bindings
- Changing error codes returned for existing errors

---

## 9. Pagination

All List methods returning potentially large collections **must** support pagination.

**Rules:**

- Use `page` (integer) and `page_size` / `pageSize` (integer or `"all"`) in the request query parameters.
- Return a structured response containing:
  - `founds`: list of items matching the query.
  - `search_options` / `searchOptions`: metadata object containing `page`, `page_size` / `pageSize`, `ordering`, and `total_count` / `totalCount`.

---

## 10. Long-Running Operations

Methods that take more than a few seconds **should** return an asynchronous operation payload instead of the resource directly.

**Pattern:**

1. Method returns an operation record immediately with a unique `id` and state `running` (HTTP 202 Accepted).
2. Client polls the operation status until `done` is true.
3. On success, `response` contains the expected resource.
4. On failure, `error` contains a standard error schema.

---

## 11. Backwards Compatibility

When modifying a stable API, the following are **non-breaking** (allowed):

- Adding a new resource, field, or method
- Adding optional request fields
- Adding fields to responses

The following are **breaking** (forbidden in a stable version):

- Removing or renaming any resource, field, or method
- Changing a field's type, format, or behavior
- Changing HTTP URL bindings
- Adding a required field to a request
- Making a previously optional field required

---

## 12. Documentation

Every public API endpoint and field **must** have clear documentation or docstrings explaining what it is and how it behaves.

**Rules:**

- Docstrings must be in English, clear, and accurate.
- Do **not** include implementation details or internal references in client-facing documentation.

---

## Quick Reference Checklist

Before finalizing an API design, verify:

- [ ] All resources are nouns; all methods are verbs
- [ ] Resource names follow `/{collection}/{id}` hierarchy
- [ ] Collection IDs are plural
- [ ] Standard methods (List, Get, Create, Update, Delete) are used wherever applicable
- [ ] Update uses PATCH, not PUT
- [ ] Request bodies accept both `camelCase` and `snake_case`
- [ ] Responses are serialized to `camelCase`
- [ ] Every resource supports Get (and List unless singleton)
- [ ] All List methods support pagination (`page`, `page_size`, `total_count`, `founds`, `search_options`)
- [ ] Timestamp fields use standard names (`created_at`, `updated_at`)

---

## Template conventions (enforced in code)

- **Pagination**: offset (`page`, `pageSize` ≤ `MAX_PAGE_SIZE`) for small user-scoped lists; cursor (`cursor`, `limit` → `{items, nextCursor}`, `BaseRepository.read_by_cursor`) for large or append-heavy tables. Never return unbounded lists.
- **Filtering**: query parameters map to `<field>__<op>` filters in the module's `Find*` schema (`eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `contains`, `in`, `isnull`); only expose filters on indexed, non-sensitive columns.
- **Sorting**: `ordering=<field>` / `-<field>`, restricted to the schema's `ORDERING_FIELDS` allow-list (422 otherwise).
- **Field selection**: prefer purpose-built list/detail schemas (e.g. `UserAdminView` vs `User`) over a generic `fields=` parameter; it keeps responses typed and cacheable.
- **Idempotency**: clients may send `Idempotency-Key` on any POST/PATCH (handled globally); endpoints with external side effects (payments, orders) should document it as required.
- **Concurrency**: single-resource GETs return `ETag`; updates accept `If-Match` (`app/core/conditional.py`).
- **Deprecation**: `dependencies=[deprecated(sunset=date(...), link=...)]` from `app/core/versioning.py`; breaking changes need a new version (ADR 0003). CI fails on breaking OpenAPI diffs.
- **Contract**: after changing routes or schemas run `uv run task openapi` and `pnpm gen:api` and commit both generated files.
