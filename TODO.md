---
name: TODO.md
description: Open collection work and server concepts that are not available to install.
---

# Open work and server concepts

- All entries follow the member rules in [`AGENTS.md`](AGENTS.md).

## Open collection work

### One lifecycle for the app products

- Align `memory-rag` with the terminal-attached lifecycle in `research-rag/AGENTS.md`.
  - Open a browser only when requested.
  - Support project selection in the workspace.
  - Implement controls in each app's own workspace and adapter, not a shared dependency.
- Related command-center work belongs in `research-rag/TODO.md`.

## Graph memory server

- Deferred while its type system and local/global boundary remain unsettled.
- Proposed model: objects, addressable relations, and atomic statements, based on the MCP reference memory server and reimplemented in Python.
  - A project-declared schema in `project-types.json`, seeded with a canonical vocabulary.
  - Reversible withdrawal and exact-duplicate refusal with a reasoned override.
  - One global store per user and explicit `scope` for promotion.
- `memory-rag` remains the installable memory product.
  - Keep this concept separate from changes to the existing memory product.

## Embedded C development server

- Implementation requires an explicit request.
- Proposed sources: chip manuals, user guides, datasheets, HTML/Markdown references, and selected C sources and headers.
  - Never execute ingested code.
- Treat registers, bit fields, addresses, reset values, access modes, commands, macros, and C symbols as entities with source evidence.
  - Combine exact entity lookup with lexical and dense retrieval.
- Required locators: document page, section, or table; code file, line, and symbol.
- Filter by vendor, product, document revision, protocol, language, and source type.
- Keep state and retrieval project-local.
- Proposed tools: status, ingestion, search, register lookup, symbol lookup, evidence retrieval, source listing, and reviewed metadata.
- Default to CPU; defer GPU support.
