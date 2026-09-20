# TODO — servers that do not exist yet

This file holds concepts for MCP servers that have *not* been built. A server is
listed in the collection `README.md` only once its repository exists, so
everything here is a design sketch rather than something you can install.

Both entries share the same rules, which come from this collection's
`AGENTS.md`:

- Each server is independently installable and self-contained: its own README,
  its own tests, its own storage, its own release history.
- No server may depend on a sibling server or read its private state.
- Deferred state lives in the project's own directory, and nothing crosses
  project boundaries.
- UltraRAG stays unmodified. Any adaptation lives in the new server, not in the
  upstream source tree.

---

## Embedded C development server

**Status:** design agreed, implementation deferred until it is explicitly asked
for.

**What it would be.** A project-scoped knowledge base for embedded C work: chip
manuals, user guides, datasheets, HTML or Markdown reference documentation, and
hand-picked C reference code. It would never execute ingested code.

**What makes it different from the research server.** Registers, bit fields,
addresses, reset values, access modes, commands, macros, and C symbols are
first-class entities with exact source evidence, not just text to search. Exact
entity lookup is combined with lexical and dense retrieval.

**Key requirements**

- Support PDFs and reference documentation, plus C sources and headers.
- Keep locators all the way back: page, section, or table for documents; file,
  line, and symbol for code.
- Make vendor, product, document revision, protocol, language, and source type
  filterable metadata.
- Keep state under each project's own directory and prevent cross-project
  retrieval.
- Expose focused tools: status, ingestion, search, register lookup, symbol
  lookup, evidence retrieval, source listing, and reviewed metadata.
- Default to CPU-only operation, with a GPU path as future work.
- Ship a standalone README and agent guidance of its own; comparison text
  belongs in the collection README only after the server exists.

---

## Memory server

**Status:** concept agreed, detailed design and implementation deferred until it
is explicitly asked for.

**What it would be.** Durable working memory for a person and their agents:
notes, interpretations, decisions, open questions, and project terminology —
distinct from the transient conversation context a client holds.

**Key requirements**

- First evaluate UltraRAG's existing memory server and expose its unmodified
  behaviour where it already fits; keep any adapter outside the upstream tree.
- Require an explicit write call before anything becomes durable. Nothing is
  saved silently.
- Record origin or author, creation and edit times, memory type, tags, and any
  user-supplied evidence references.
- Treat an evidence reference as a provenance link, never as proof that the
  memory is a source. Remembered text must never be presented as document
  evidence.
- Expose tools for status, create, search, list, retrieve, update, and delete,
  with deletion and editing visible to the user.
- Default to CPU-only local retrieval with no required external database, and
  decide between lexical, dense, and hybrid retrieval only after evaluation.
- Do not depend on the research server, its tools, or its private storage.
- Ship a user README, agent guide, engineering contract, storage documentation,
  tests, and versioning before it appears in the collection README.
