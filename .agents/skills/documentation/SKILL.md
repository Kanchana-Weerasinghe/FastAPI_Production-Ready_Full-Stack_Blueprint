---
name: documentation
description: Standards for code documentation, docstrings, and maintaining README files.
---
# Documentation Skill

## Code Documentation

- Add professional, clear docstrings to all major classes and functions.
- Explain the "Why" and not just the "What".

## READMEs

- Maintain up-to-date README files in both the `server` and `web` directories detailing how to run the development servers and tests.
- Document any environment variable requirements clearly.

## API Documentation (`docs/API_FLOW.md`)

You must update [docs/API_FLOW.md](docs/API_FLOW.md) if **anything changes in the API** (e.g., creating new routes, updating existing endpoints, or changing schemas/parameters). The updates must follow the exact format given in `docs/API_FLOW.md`:

- **Heading**: Must say `# API Document and Flow Diagram`.
- **Index**: Must contain a clickable index of all the created APIs pointing to the corresponding details blocks.
- **API Details Structure**: Use HTML `<details>` and `<summary>` tags to format each API as an accordion:
  - Inside the main `<details>` block, include a markdown table summarizing:
    - `URL`
    - `Method`
    - `Auth Required`
    - `Description`
  - Nest three separate `<details>` blocks under a blockquote (`>`) for the Request, Response, and Error JSON bodies:
    - `Request body` (or query/payload details) listing each field, its data type, **Required** or *Optional* status, alternative alias/name accepted (e.g. snake_case names for camelCase parameters if supported by the backend model configuration), description, and an example JSON payload.
    - `Response body` containing the successful response JSON schema/example.
    - `Error body` containing potential error JSON structures (e.g., 401, 404, 422, 429) and when they will arrive.
  - Nest another `<details>` block containing a colorful, sequential `mermaid` flowchart showing the numbered request flow (e.g., `1. POST ->`, `2. Validate ->`, `3. INSERT ->`, etc.) without circular paths.

## Database Design Documentation (`docs/DATABASE_DESIGN.md`)

You must update [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md) if **anything changes in the `services/core-api/app/models` folder** (e.g., adding/modifying SQLAlchemy models, tables, columns, or relationships). The updates must follow the exact format given in `docs/DATABASE_DESIGN.md`:

- **Entity Relationship Diagram**: Maintain a **Mermaid Entity Relationship Diagram** representing all tables, columns, and relationships (with keys and descriptions). Only standard key constraints (`PK`, `FK`) are permitted (do not use invalid constraints like `UK`).
- **Tables and Columns Detail**: Provide a detailed tabular reference listing every column, its data type, constraints, and a comprehensive comment explaining **why** it is there.

## Markdown Formatting Rules

- **Headings**: Ensure there is a blank line (gap) before and after any heading (e.g., `#`, `##`, `###`).
- **Lists**: All ordered and unordered lists must start with `-`. There must be a blank line (gap) before the start of the list and after the complete list ends.
