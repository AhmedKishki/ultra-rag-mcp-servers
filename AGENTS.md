# AGENTS.md

This is a collection repository. Its server implementations, its research app, and its shared libraries are Git submodules and independent projects:

- `vanilla-ultra-rag-mcp-server/`
- `research-ultra-rag-mcp-server/`
- `research-rag/`
- `memory-ultra-rag-mcp-server/`
- `ui-ultra-rag-mcp/`

## Working rules

- Write every file — documents, commit messages, code comments — in direct, concise language: one sentence per fact, no filler, no selling, and never restate a title as its own first sentence.
- Retain the prominent UltraRAG acknowledgement in `README.md`, the root `NOTICE`, upstream project links, license information, and independent-project disclaimer. Do not imply upstream endorsement.
- Read the selected submodule's own `AGENTS.md` before changing its code.
- Make, test, commit, and push implementation changes inside the child repository first.
- Update a submodule pointer here only after its referenced commit is available from the child's remote repository.
- Do not duplicate child source files in the parent or couple their release histories.
- Keep the parent limited to collection-level documentation, automation, and pinned submodule references.
- Treat `ui-ultra-rag-mcp` as shared interface infrastructure, not as an MCP server. A repository may depend on a pinned UI commit through a thin adapter, but the UI must never read a project's private storage directly.
- `research-rag` is an app, not a collection member that is exempt from the rules here. It is a server product with a browser workspace and a command line beside its agent surface, and it holds the same obligations as every other member: its own README, agent guidance, storage boundary, tests, and release history, and no dependency on a sibling's private state.
- `research-rag` and `research-ultra-rag-mcp-server` read and write the same project layout while both ship. The shared layout, the shared settings directory, and the shared model cache are deliberate and pinned in the app's own `AGENTS.md`; two products serving one project must never signal each other's processes, and each generates its launcher under its own name.
- Keep cross-project comparisons and selection guidance in the parent `README.md`. Each child `README.md` must stand alone and document only that project.
- Keep deferred, unimplemented server concepts in the collection-root `TODO.md`; list a server in `README.md` only after its repository has been created and included here. Child roadmaps may cover deferred work only within that child's existing role, not concepts for new servers.
- Every server, including planned servers, must be an independently installable, self-contained project with its own README, agent guidance, storage boundary, tests, and release history. Do not make one specialized server depend on a sibling server or its private state.
- Commit and push after every change, without waiting to be asked. A change that is not on its remote is a change that is lost, and it is this repository's only record. Push the child repository first, then the pointer here, in two commands rather than one batch at the end.
- Do not edit `.gitmodules` casually; the canonical child remotes are the AhmedKishki GitHub repositories named above.

## Validation

Before committing a collection change, run:

```bash
git submodule status --recursive
git -C vanilla-ultra-rag-mcp-server status --short --branch
git -C research-ultra-rag-mcp-server status --short --branch
git -C research-rag status --short --branch
git -C memory-ultra-rag-mcp-server status --short --branch
git -C ui-ultra-rag-mcp status --short --branch
git diff --check
```

A leading `-` in `git submodule status` means a child is not initialized. A leading `+` means the checked-out child commit differs from the commit recorded by the parent. A submodule listed in `git submodule status` that is absent from this file was removed, and its entry in `.gitmodules` and its gitlink are gone with it.

`research-rag` runs as a long-lived process on a loopback port, which a stdio server does not. Before changing a child that serves a project, check whether the app is up for it: `research-rag --project-root <project> clients` answers with the app's address and the agents attached to it, and answers that nothing is running without starting one.
