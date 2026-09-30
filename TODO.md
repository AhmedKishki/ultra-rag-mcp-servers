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

**What makes it different from the research server.** Registers, bit fields, addresses, reset values, access modes, commands, macros, and C symbols are first-class entities with exact source evidence rather than text to search. Exact entity lookup is combined with lexical and dense retrieval.

**Key requirements**

- Support PDFs and reference documentation, plus C sources and headers.
- Keep locators all the way back: page, section, or table for documents; file, line, and symbol for code.
- Make vendor, product, document revision, protocol, language, and source type filterable metadata.
- Keep state under each project's own directory and prevent cross-project retrieval.
- Expose focused tools: status, ingestion, search, register lookup, symbol lookup, evidence retrieval, source listing, and reviewed metadata.
- Default to CPU-only operation, with a GPU path as future work.
- Ship a standalone README and agent guidance of its own; comparison text belongs in the collection README only after the server exists.

---

## Retire or coexist with `research-ultra-rag-mcp-server`

**Status:** open since the research app was created, 2026-09-30.

`research-rag` is the same engine, the same storage layout, and the same seven agent operations as `research-ultra-rag-mcp-server`, packaged as an app: one process per project serving a workspace, an agent surface, and a command line on one loopback port. Both read and write the same `.research-rag` directory, both generate a launcher into the project root under different names, and neither will signal the other's processes.

**What has to be decided.** Whether the app replaces the server, or the two coexist. Coexistence is the current state and it costs something specific: two products, one layout, one settings directory, one model cache, and no check that the two agree about a state version. A field this app writes that the server cannot parse is a reader answering with state it could not have written, which is the fault class a stale checkout already caused once.

**What is not deferred.** The compatibility that makes coexistence safe today is pinned and tested in the app's own `AGENTS.md` and `tests/test_data_roots.py`. It is not a reason to prefer coexistence.

**The direction the app's README and AGENTS.md both point at.** `research-rag` is the form to install; the server is what an agent-facing MCP entry points at. If that holds, retiring the server means deleting a repository, not migrating a project, because the layout is byte-compatible and the app keeps the names the server wrote.

**The standalone-browser case has one open question.** An agent whose MCP client cannot open a socket needs the stdio bridge, which the app provides. What is not yet settled is whether the server should gain the same bridge, or whether it should simply be retired and its readers moved to `research-rag mcp`.
