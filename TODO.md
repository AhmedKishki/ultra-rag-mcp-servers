---
name: TODO.md
description: Open work the collection owns, and server concepts that are not available to install.
---

# Open work and server concepts

- All entries follow the member rules in [`AGENTS.md`](AGENTS.md).
- This file holds work the collection itself owns. Work inside a member belongs in that member's own `TODO.md`.

## The shared development environment

- [ ] **Prepare both members' environments from the collection root.** Feature. A recursive clone gives two working trees and two environments to create by hand, and nothing records the interpreter each member is tested against. One command that syncs and verifies each member's environment turns the collection into a development environment rather than a directory of checkouts.

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
