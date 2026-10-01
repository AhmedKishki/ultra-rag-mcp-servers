# TODO — projects that do not exist yet, and open collection work

Concepts for MCP servers that have *not* been built. A server is listed in the collection `README.md` only once its repository exists, so everything here is a design sketch rather than something you can install.

Each entry follows the member rules in the collection's `AGENTS.md`, and that file is the owner of them.

---

## Graph memory server

- **Status:** the server is parked, its submodule is removed, and its definition is still being revised.
- **What it would be:** a project-scoped, strongly typed store for durable operational memory between agent sessions, holding objects, relations as addressable atoms, and atomic statements.
  - It would be the MCP reference memory server's model reimplemented in Python, extended with a project-declared type schema in `project-types.json` seeded with a canonical vocabulary, addressed relations, reversible withdrawal, admission control that refuses an exact duplicate and records a reasoned override, one global store per user, and promotion across that line behind an explicit `scope`.
- **Why it is not built:** the type system and the local/global boundary are the open questions, and the memory app already answers the simpler version of them.
  - `memory-rag` is the collection's memory product until this one is settled, and the server behind it is frozen, so a new memory concept starts here rather than in either of them.

---

## Embedded C development server

- **Status:** design agreed, implementation deferred until it is explicitly asked for.
- **What it would be:** a project-scoped knowledge base for embedded C work: chip manuals, user guides, datasheets, HTML or Markdown reference documentation, and hand-picked C reference code.
  - It would never execute ingested code.
- **What makes it different from the research app:** registers, bit fields, addresses, reset values, access modes, commands, macros, and C symbols are first-class entities with exact source evidence rather than text to search.
  - Exact entity lookup is combined with lexical and dense retrieval.
- **Key requirements:**
  - The knowledge base would accept PDFs and reference documentation, alongside C sources and headers.
  - Every locator would reach back to a page, section, or table in a document, and to a file, line, and symbol in code.
  - Vendor, product, document revision, protocol, language, and source type would all be filterable metadata.
  - Each project would keep its state under its own directory, and no retrieval would cross a project boundary.
  - The tool surface would stay focused: status, ingestion, search, register lookup, symbol lookup, evidence retrieval, source listing, and reviewed metadata.
  - Operation would default to CPU-only, with a GPU path left as future work.
  - The server would ship a standalone README and its own agent guidance, and comparison text would enter the collection README only after the server exists.
