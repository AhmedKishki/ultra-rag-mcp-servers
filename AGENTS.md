# AGENTS.md

This is a collection repository. Its two MCP server implementations and shared UI library are Git submodules and independent projects:

- `vanilla-ultra-rag-mcp-server/`
- `research-ultra-rag-mcp-server/`
- `ui-ultra-rag-mcp/`

## Working rules

- Retain the prominent UltraRAG acknowledgement in `README.md`, the root `NOTICE`, upstream project links, license information, and independent-project disclaimer. Do not imply upstream endorsement.
- Read the selected submodule's own `AGENTS.md` before changing its code.
- Make, test, commit, and push implementation changes inside the child repository first.
- Update a submodule pointer here only after its referenced commit is available from the child's remote repository.
- Do not duplicate child source files in the parent or couple their release histories.
- Keep the parent limited to collection-level documentation, automation, and pinned submodule references.
- Treat `ui-ultra-rag-mcp` as shared interface infrastructure, not as an MCP server. Server repositories may depend on a pinned UI commit through a thin adapter, but the UI must never read a server's private storage directly.
- Keep cross-server comparisons and selection guidance in the parent `README.md`. Each child `README.md` must stand alone and document only that server.
- Keep deferred, unimplemented server concepts in the collection-root `TODO.md`; list a server in `README.md` only after its repository has been created and included here. Child roadmaps may cover deferred work only within that child's existing role, not concepts for new servers.
- Every server, including planned servers, must be an independently installable, self-contained project with its own README, agent guidance, storage boundary, tests, and release history. Do not make one specialized server depend on a sibling server or its private state.
- Do not edit `.gitmodules` casually; the canonical child remotes are the AhmedKishki GitHub repositories named above.

## Validation

Before committing a collection change, run:

```bash
git submodule status --recursive
git -C vanilla-ultra-rag-mcp-server status --short --branch
git -C research-ultra-rag-mcp-server status --short --branch
git -C ui-ultra-rag-mcp status --short --branch
git diff --check
```

A leading `-` in `git submodule status` means a child is not initialized. A leading `+` means the checked-out child commit differs from the commit recorded by the parent.
