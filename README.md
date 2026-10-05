---
name: README.md
description: Compare the included UltraRAG projects and manage their pinned repositories.
---

# UltraRAG MCP servers

- Two independent apps, included as Git submodules at specific commits.
- This repository is their shared development environment: one checkout holds both working trees, and [`scripts/`](scripts/) holds the automation that spans them.
  - Each app keeps its own environment, tests, and releases.

## Credit to UltraRAG

- Built on [`OpenBMB/UltraRAG`](https://github.com/OpenBMB/UltraRAG)'s MCP architecture and RAG implementation.
- UltraRAG credits [`THUNLP`](https://nlp.csai.tsinghua.edu.cn/) at Tsinghua University, [`NEUIR`](https://neuir.github.io/) at Northeastern University, [`OpenBMB`](https://www.openbmb.cn/home), [`AI9stars`](https://github.com/AI9Stars), and the [`UltraRAG contributors`](https://github.com/OpenBMB/UltraRAG/graphs/contributors).
- UltraRAG uses the [`Apache License 2.0`](https://github.com/OpenBMB/UltraRAG/blob/main/LICENSE.txt).
- These projects are not official UltraRAG releases and are not affiliated with or endorsed by the upstream organizations.
  - See [`NOTICE`](NOTICE) and each child's notice for attribution and dependency terms.

## Included projects

| Project | Scope and interface | Pick it when |
|---|---|---|
| [`research-rag`](research-rag/) | PDF/EPUB evidence retrieval on CPU, designed for tens to low hundreds of sources. One process per project serves a browser workspace, MCP, and a CLI. | You need to find and cite passages from original documents. This is the collection's only research product. |
| [`memory-rag`](memory-rag/) | One account-wide process serves global memory and registered projects' local memories. Browser workspace, CLI, per-kind MCP tools, cross-kind recall, and exact-text forgetting. | You need memory across agent sessions and a central workspace to inspect and repair it. This is the collection's memory product. |

- Both apps serve loopback HTTP and offer a stdio bridge addressed by project name.
  - Attached agent clients can be listed and disconnected.
- Both apps keep memory in the same SQLite records under `.memory-rag` and `memory/default`.
  - `MEMORY.md` is a rendering, not the authoritative record.
  - Embedding and reranking run locally, without a hosted model API.
  - Recall searches both scopes; forgetting requires exact, unambiguous text.
  - The memory app's SQL console permits unrestricted reads and bounded statement edits followed by reindexing.
- Each project's README owns its installation, configuration, commands, and limits.
- Unimplemented server concepts belong in [`TODO.md`](TODO.md).

### Comparison outside the collection

- [`mcp-rag-server`](https://github.com/kwanLeeFrmVi/mcp-rag-server) is a separate project for text, Markdown, JSON, JSONL, and CSV context retrieval.
  - It runs through Node/npm and uses an HTTP embedding endpoint, such as local Ollama or a hosted provider.
- Choose `research-rag` for PDF/EPUB evidence with original-file locators, reviewed metadata, and in-process local models.
  - Consult the other project's README for its current configuration and limits.

## What each app owns

- Each app carries its own workspace and settings-layer implementation.
  - Carry shared fixes to both copies.
- Only `research-rag` carries the gateway to UltraRAG's Vanilla RAG stages.
- `research-rag` pins an author-hosted `bm25s` fork for a non-ASCII stopword fix.
  - Its `AGENTS.md` states the condition for returning to upstream.

## Clone the complete collection

- Clone all projects:

  ```bash
  git clone --recurse-submodules https://github.com/AhmedKishki/ultra-rag-mcp-servers.git
  cd ultra-rag-mcp-servers
  ```

- Initialize an existing clone's missing submodules:

  ```bash
  git submodule update --init --recursive
  ```

## Pull collection updates

- Pull the collection's selected revisions:

  ```bash
  git pull --ff-only
  git submodule update --init --recursive
  ```

- The parent pins exact child commits; this does not advance children to their branch heads.

## Work on one server

- Follow the child's guidance and the release order in [`AGENTS.md`](AGENTS.md).
- After the tested child commit is pushed, record its pointer here:

  ```bash
  git -C research-rag switch main
  git -C research-rag pull --ff-only origin main
  git add research-rag
  git commit -m "Update research-rag"
  git push
  ```

- Substitute another child name when updating that project.

## Stop stray server processes

- Prefer an app's own `stop` command or disconnect a server from its MCP client.
- `scripts/stop-servers.sh` is a Linux cleanup tool for recognized app, server, gateway, and UltraRAG processes.
  - It recognizes this collection's console scripts, including ones from earlier revisions that no current member installs, so a machine still running one is cleaned up too.
  - Signaling requires Python 3.9 or newer and Linux 5.3 or newer with usable pidfds.
  - Without a signal handle it leaves the process alone and exits with code 3.
  - Inspect the dry run before stopping anything.
  - It sends `SIGTERM`, then `SIGKILL` after the timeout to surviving selected processes.

  ```bash
  scripts/stop-servers.sh --dry-run
  scripts/stop-servers.sh
  scripts/stop-servers.sh --project "/path/to/project"
  scripts/stop-servers.sh --timeout 30
  ```

- The project filter selects processes with that project root and their recognized descendants.
  - It does not stop the account-wide memory app merely because that app serves the project.
- The script reports roles and family depth, and exits nonzero if selected processes survive.
- Restart an app with its CLI, or reconnect its server from the MCP client.
