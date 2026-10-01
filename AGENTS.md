# AGENTS.md

This is a collection repository. Its server implementations, its research app, and its shared libraries are Git submodules and independent projects:

- `vanilla-ultra-rag-mcp-server/`
- `research-ultra-rag-mcp-server/` — frozen; see "The frozen research server" below
- `research-rag/` — the form to install for the research knowledge base, and the only one of the two that changes
- `memory-ultra-rag-mcp-server/` — frozen; see "The frozen memory server" below
- `memory-rag/` — the form to install for the account's memory, and the only one of the two that changes
- `ui-ultra-rag-mcp/`
- `config-ultra-rag-mcp/`

## Working rules

- Write every file — documents, commit messages, code comments — in direct, concise language: one sentence per fact, no filler, no selling, and never restate a title as its own first sentence.
- Retain the prominent UltraRAG acknowledgement in `README.md`, the root `NOTICE`, upstream project links, license information, and independent-project disclaimer. Do not imply upstream endorsement.
- Read the selected submodule's own `AGENTS.md` before changing its code.
- Make, test, commit, and push implementation changes inside the child repository first.
- Update a submodule pointer here only after its referenced commit is available from the child's remote repository.
- Do not duplicate child source files in the parent or couple their release histories.
- Keep the parent limited to collection-level documentation, automation, and pinned submodule references.
- Treat `ui-ultra-rag-mcp` and `config-ultra-rag-mcp` as shared libraries, not as MCP servers. A repository may depend on a pinned commit through a thin adapter, but neither may read a project's private storage directly.
- `research-rag` is an app, not a collection member that is exempt from the rules here. It is a server product with a browser workspace and a command line beside its agent surface, and it holds the same obligations as every other member: its own README, agent guidance, storage boundary, tests, and release history, and no dependency on a sibling's private state.
- `research-rag` and the frozen `research-ultra-rag-mcp-server` read and write the same project layout. The shared layout, the shared settings directory, and the shared model cache are deliberate and pinned in the app's own `AGENTS.md`; two products serving one project must never signal each other's processes, and each generates its launcher under its own name.
- `memory-rag` is an app, and it holds the same obligations as `research-rag`. It is one process for the account rather than one per project, because a memory has a scope every project shares and a command center that had to be visited once per repository would not be a central place for anything.
- `memory-rag` and the frozen `memory-ultra-rag-mcp-server` read and write the same memory directories, and the settings directory, the environment prefix, the model cache, and the scope directory names are shared deliberately. The frozen product holds no user dimension, and neither product adds one.
- Keep cross-project comparisons and selection guidance in the parent `README.md`. Each child `README.md` must stand alone and document only that project.
- Keep deferred, unimplemented server concepts in the collection-root `TODO.md`; list a server in `README.md` only after its repository has been created and included here. Child roadmaps may cover deferred work only within that child's existing role, not concepts for new servers.
- Every server, including planned servers, must be an independently installable, self-contained project with its own README, agent guidance, storage boundary, tests, and release history. Do not make one specialized server depend on a sibling server or its private state.
- Commit and push after every change, without waiting to be asked. A change that is not on its remote is a change that is lost, and it is this repository's only record. Push the child repository first, then the pointer here, in two commands rather than one batch at the end.
- Do not edit `.gitmodules` casually; the canonical child remotes are the AhmedKishki GitHub repositories named above.

## The frozen research server
`research-ultra-rag-mcp-server` is frozen: no change is made to it, and none is planned. It stays in this collection as a submodule because the machines that run it read and write the same `.research-rag` projects the app reads and writes, so a project those machines still open is a project the app must not make unreadable.

- Never open a change, a branch, or a pull request against it. A fix a reader needs goes into `research-rag`.
- Never bump its pinned submodule commit. Its pointer is frozen at the revision that shipped, because moving it is a change to a product that is not changing.
- Never change the shared on-disk layout to serve the app's own needs. A field or schema version the frozen product cannot parse is a project neither product can be trusted to read, and that is the fault class a stale checkout already caused once. Extend `project.json` additively, because that is the one portable file the frozen product reads a known subset of; do not add a field to `source-metadata.json` or `source-catalog.json`, because the frozen product refuses a field it does not know.
- Do not remove the submodule, and do not delete the repository. Keeping it is what makes a machine that runs both products work.

## The frozen memory server
`memory-ultra-rag-mcp-server` is frozen: no change is made to it, and none is planned. It stays in this collection as a submodule because the machines that run it read and write the same memories the app reads and writes, so a memory those machines still hold is a memory the app must not make unreadable.

- Never open a change, a branch, or a pull request against it. A fix a reader needs goes into `memory-rag`.
- Never bump its pinned submodule commit. Its pointer is frozen at the revision that shipped, because moving it is a change to a product that is not changing.
- Never rename anything the frozen product looks up by name: the account's settings directory, the `MEMORY_ULTRARAG_` environment prefix, the model cache, or the `memory/default` and `.memory-rag` directory names. A rename strands every existing memory and forces a silent model re-download, and the frozen product would keep writing the old path. `memory-rag`'s own `AGENTS.md` states each one as load-bearing and its tests fail if any moves.
- Do not change `memory.sqlite3`'s schema to serve the app's own needs. The record is the statements, and the frozen product reads the same tables; a column it cannot read is a memory it cannot serve. `memory-rag`'s SQL panel writes statements and reindexes for exactly this reason.
- A defect in it is fixed in `memory-rag`, and the fix is documented there rather than here.

## Validation

Before committing a collection change, run:

```bash
git submodule status --recursive
git -C vanilla-ultra-rag-mcp-server status --short --branch
git -C research-rag status --short --branch
git -C memory-rag status --short --branch
git -C ui-ultra-rag-mcp status --short --branch
git -C config-ultra-rag-mcp status --short --branch
git diff --check
```

Both frozen servers, `research-ultra-rag-mcp-server` and `memory-ultra-rag-mcp-server`, are deliberately absent from that list: their checkouts are expected to stay where they are, and `git submodule status` is the check that their pointers have not moved.

A leading `-` in `git submodule status` means a child is not initialized. A leading `+` means the checked-out child commit differs from the commit recorded by the parent. A submodule listed in `git submodule status` that is absent from this file was removed, and its entry in `.gitmodules` and its gitlink are gone with it.

`research-rag` runs as a long-lived process on a loopback port, which a stdio server does not. Before changing a child that serves a project, check whether the app is up for it: `research-rag --project-root <project> clients` answers with the app's address and the agents attached to it, and answers that nothing is running without starting one.

`memory-rag` does the same for an account rather than a project, and it is one process for every project rather than one each: `memory-rag clients` answers with its address and the agents attached to it. Its writes reach the same records the frozen server writes, so a hand edit made through the SQL panel is visible to a stdio client still running the frozen product, and the reverse.
