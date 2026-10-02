# AGENTS.md

The working rules of this collection: what a change here has to be argued against, and what this repository owes the machines that already run what it holds.

This is a collection repository. Its server implementations and its apps are Git submodules and independent projects:

- `research-rag/` — the form to install for the research knowledge base, and the only research product here
- `memory-ultra-rag-mcp-server/`
- `memory-rag/` — the form to install for the account's memory

## Working rules

### How to write

- Write every file — documents, commit messages, code comments — in direct, concise language.
  - One sentence per fact, no filler, no selling, and never restate a title as its own first sentence.
- Retain the prominent UltraRAG acknowledgement in `README.md`, the root `NOTICE`, upstream project links, license information, and independent-project disclaimer.
  - Do not imply upstream endorsement.
- Markdown describes the present.
  - A finished item leaves no trace except the code and the commit.

### Where a fact belongs

- Read the selected submodule's own `AGENTS.md` before changing its code.
- Keep cross-project comparisons and selection guidance in the parent `README.md`.
  - Each child `README.md` must stand alone and document only that project.
- Keep deferred, unimplemented server concepts in the collection-root `TODO.md`.
  - List a server in `README.md` only after its repository has been created and included here.
  - Child roadmaps may cover deferred work only within that child's existing role, not concepts for new servers.
- Do not duplicate child source files in the parent or couple their release histories.
  - Keep the parent limited to collection-level documentation, automation, and pinned submodule references.

### What a member must be

- Every server, including planned servers, must be an independently installable, self-contained project.
  - Its own README, agent guidance, storage boundary, tests, and release history.
  - Do not make one specialized server depend on a sibling server or its private state.
- No member depends on another project of this collection's author to do its work.
  - The workspace, the settings layer, and the vanilla gateway were shared libraries, and each app that needs one carries its own copy.
  - Two copies of the workspace and the settings layer is duplication this repository accepts, because a pinned dependency is a fix this repository cannot make and cannot ship.
  - A change that belongs in one member is made in that member, and where another member carries the same code it is carried there too.
- `research-rag` is an app, not a collection member that is exempt from these rules.
  - It is a server product with a browser workspace and a command line beside its agent surface, and it holds the same obligations as every other member.
  - It has no dependency on a sibling's private state.
- `memory-rag` is an app, and it holds the same obligations as `research-rag`.
  - It is one process for the account rather than one per project, because a memory has a scope every project shares.
  - A command center that had to be visited once per repository would not be a central place for anything.

### Where two memory products share state

- `memory-rag` and `memory-ultra-rag-mcp-server` read and write the same memory directories.
  - The settings directory, the environment prefix, the model cache, and the scope directory names are shared deliberately.
  - The server holds no user dimension, and neither product adds one.

### How to record a change

- Make, test, commit, and push implementation changes inside the child repository first.
- Update a submodule pointer here only after its referenced commit is available from the child's remote repository.
- Commit and push after every change, without waiting to be asked.
  - A change that is not on its remote is a change that is lost, and it is this repository's only record.
  - Push the child repository first, then the pointer here, in two commands rather than one batch at the end.
- Do not edit `.gitmodules` casually.
  - The canonical child remotes are the AhmedKishki GitHub repositories named above.

## What this repository may do with a member

This repository is the master repository for every project it holds. A member's code, tests, documentation, and releases are changed here, run here, and debugged here, and a member is added, retired, or archived as the work requires.

- No member is frozen, and no pointer is held at a revision for the sake of holding it.
  - A product installed on a machine is a reason to keep it installable, not a reason the master repository may not change it.
  - A defect in a member is fixed in that member, and the fix is pushed to that member's remote before the pointer here moves.
- What binds is the state a live machine already holds.
  - `memory-rag` and `memory-ultra-rag-mcp-server` read and write the same memory directories, so a change that would leave an existing memory unreadable is a change neither product may make.
  - The account's settings directory, the `MEMORY_ULTRARAG_` environment prefix, the model cache, and the `memory/default` and `.memory-rag` directory names are found by name, and a rename strands every memory that exists under the old one.
  - `memory.sqlite3`'s columns are read by both products, so a column one cannot read is a memory it cannot serve.
  - `memory-rag`'s own `AGENTS.md` states each of those names as load-bearing, and its tests fail if any moves.

## Validation

Before committing a collection change, run:

```bash
git submodule status --recursive
git -C research-rag status --short --branch
git -C memory-rag status --short --branch
git -C memory-ultra-rag-mcp-server status --short --branch
git diff --check
```

Reading that output:

- A leading `-` means a child is not initialized.
- A leading `+` means the checked-out child commit differs from the commit recorded by the parent.
- A submodule listed in `git submodule status` that is absent from this file was removed, and its entry in `.gitmodules` and its gitlink are gone with it.

Before changing a child that serves a project, check whether the app is up for it:

- `research-rag` runs as a long-lived process on a loopback port, which a stdio server does not.
  - `research-rag --project-root <project> clients` answers with the app's address and the agents attached to it.
  - It answers that nothing is running without starting one.
- `memory-rag` does the same for an account rather than a project, and it is one process for every project rather than one each.
  - `memory-rag clients` answers with its address and the agents attached to it.
  - Its writes reach the same records the memory server writes, so a hand edit made through the SQL panel is visible to a stdio client still running the server, and the reverse.
