---
name: AGENTS.md
description: Collection boundaries, compatibility rules, and validation for changes across the child repositories.
---

# Collection rules

## Scope

- This repository holds two independently versioned Git submodules:
  - `research-rag/`: the research app and the collection's only research product.
  - `memory-rag/`: the account-wide memory app.
- Read a child's `AGENTS.md` before changing it.
- Keep the parent limited to collection documentation, automation, and submodule references.
  - Do not copy child source into the parent or couple release histories.
- Members may be changed, added, retired, or archived here.
  - No member's code is frozen because an installed machine runs it.
  - Preserve the state those machines already hold.
  - A retired member keeps its own repository and stays installable.
    - Its records stay readable by the product that replaced it.

## Documentation

- Write direct, concise sentences with one fact each.
  - Cut filler, sales language, and repetition of a heading.
- Preserve the prominent UltraRAG credit in `README.md`, `NOTICE`, upstream links, license information, and independent-project disclaimer.
  - Never imply upstream endorsement.
- Markdown describes current rules and capabilities; Git holds completed work.
- Keep comparisons and selection guidance in the parent `README.md`.
  - Child READMEs stand alone and describe only their project.
- Keep unimplemented server concepts in the root `TODO.md`.
  - List a server in `README.md` only after its repository exists and is included.
  - Child roadmaps cover only work within that child's role.

## Independence

- Every existing or planned member must own its installation, README, agent guidance, storage boundary, tests, and release history.
- No member may depend on a sibling server or its private state.
- Members must not depend on another project by this collection's author to do their work.
  - Each app carries the workspace, settings layer, and gateway it needs.
  - Local copies of workspace and settings code are deliberate.
  - Carry a fix to every member holding the affected code.
- These rules apply equally to both apps.
- `research-rag` serves one process per project; `memory-rag` serves one per account.

## Shared memory compatibility

- `memory-rag` reads and writes records the retired stdio server also wrote.
  - Neither product adds a user dimension.
- Preserve existing settings and storage names:
  - The account's settings directory, `MEMORY_ULTRARAG_` environment prefix, and model cache.
  - The `memory/default` and `.memory-rag` scope directories.
  - The shared columns of `memory.sqlite3`.
- A change must leave memory written by the retired server readable.
  - The child guidance and compatibility tests hold the detailed contract.

## Recording changes

- Make, test, commit, and push a child's changes before updating its parent pointer.
- Update a gitlink only after the referenced commit is available from the child's remote.
- Commit and push after each change, without waiting to be asked.
  - Push the child and then the parent in separate commands.
- Change `.gitmodules` only for an intentional membership or remote change.
  - Canonical child remotes are the matching AhmedKishki GitHub repositories.

## Validation

- Before changing an app, inspect its running instance without starting one:

  ```bash
  research-rag --project-root <project> clients
  memory-rag clients
  ```

- The memory app's SQL writes and the retired stdio server's writes reached the same records.
- Before committing a collection change, run:

  ```bash
  git submodule status --recursive
  git -C research-rag status --short --branch
  git -C memory-rag status --short --branch
  git diff --check
  ```

- In submodule status, `-` means uninitialized and `+` means the checkout differs from the recorded commit.
- When removing a member, remove both its `.gitmodules` entry and gitlink.
