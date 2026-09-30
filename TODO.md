# TODO — projects that do not exist yet, and open collection work

This file holds concepts for MCP servers that have *not* been built. A server is listed in the collection `README.md` only once its repository exists, so everything here is a design sketch rather than something you can install.

Every entry here follows the same rules, which come from this collection's `AGENTS.md`:

- Each server is independently installable and self-contained: its own README, its own tests, its own storage, its own release history.
- No server may depend on a sibling server or read its private state.
- Deferred state lives in the project's own directory, and nothing crosses project boundaries.
- UltraRAG stays unmodified. Any adaptation lives in the new server, not in the upstream source tree.

---

## Graph memory server

**Status:** parked 2026-09-22, submodule removed, definition still being revised.

**What it would be.** A project-scoped, strongly typed store for durable operational memory between agent sessions: objects, relations as addressable atoms, and atomic statements. It is the MCP reference memory server's model reimplemented in Python, extended with a project-declared type schema in `project-types.json` seeded with a canonical vocabulary, addressed relations, reversible withdrawal, admission control that refuses an exact duplicate and records a reasoned override, one global store per user, and promotion across that line behind an explicit `scope`.

**Why it is not built.** The type system and the local/global boundary are the open questions, and the memory server already answers the simpler version of them. `memory-ultra-rag-mcp-server` is the collection's memory server until this one is settled.

---

## Embedded C development server

**Status:** design agreed, implementation deferred until it is explicitly asked for.

**What it would be.** A project-scoped knowledge base for embedded C work: chip manuals, user guides, datasheets, HTML or Markdown reference documentation, and hand-picked C reference code. It would never execute ingested code.

**What makes it different from the research app.** Registers, bit fields, addresses, reset values, access modes, commands, macros, and C symbols are first-class entities with exact source evidence rather than text to search. Exact entity lookup is combined with lexical and dense retrieval.

**Key requirements**

- Support PDFs and reference documentation, plus C sources and headers.
- Keep locators all the way back: page, section, or table for documents; file, line, and symbol for code.
- Make vendor, product, document revision, protocol, language, and source type filterable metadata.
- Keep state under each project's own directory and prevent cross-project retrieval.
- Expose focused tools: status, ingestion, search, register lookup, symbol lookup, evidence retrieval, source listing, and reviewed metadata.
- Default to CPU-only operation, with a GPU path as future work.
- Ship a standalone README and agent guidance of its own; comparison text belongs in the collection README only after the server exists.
