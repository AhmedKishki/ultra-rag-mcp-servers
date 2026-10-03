# UltraRAG MCP servers

This repository is the collection point for independent MCP servers and apps built around UltraRAG. Each project lives in its own Git repository and is included here as a Git submodule pinned to a specific, tested commit.

## Credit to UltraRAG

The MCP servers are directly based on [`OpenBMB/UltraRAG`](https://github.com/OpenBMB/UltraRAG). UltraRAG's upstream team describes it as a joint project of [`THUNLP`](https://nlp.csai.tsinghua.edu.cn/) at Tsinghua University, [`NEUIR`](https://neuir.github.io/) at Northeastern University, [`OpenBMB`](https://www.openbmb.cn/home), and [`AI9stars`](https://github.com/AI9Stars), together with the [`UltraRAG contributors`](https://github.com/OpenBMB/UltraRAG/graphs/contributors). Their work provides the MCP architecture and RAG implementation underlying this collection.

UltraRAG is licensed under the [`Apache License 2.0`](https://github.com/OpenBMB/UltraRAG/blob/main/LICENSE.txt). These are independent projects, not official UltraRAG releases, and are not affiliated with or endorsed by the upstream organizations. See [`NOTICE`](NOTICE) and the notice inside each server repository for version-specific attribution.

## Included projects

This README is the collection-level comparison and selection guide. Each server's own README is a standalone user manual for that server and does not compare it with the other projects in this collection.

| Project | What it is | Pick it when |
|---|---|---|
| [`research-rag`](research-rag/) | A research knowledge base over your own PDF and EPUB collection, as an installed application: one process per project serving a browser workspace, an MCP agent surface, and a command line on one loopback port, plus a stdio bridge for a client that cannot open a socket, which takes a project name rather than a path so one entry works on any machine holding that project. **This is the only research product in this collection, and it is the form to install.** | You want to find, narrow, and cite evidence in a document collection, at the scale of tens to low hundreds of sources on a CPU, and you read it in a browser, drive it from a terminal, or hand it to an agent. |
| [`memory-rag`](memory-rag/) | The account's global memory and every registered project's local memory, as an installed application: **one** process holding them all and serving a browser workspace, an MCP agent surface, and a command line on one loopback port. A project is registered by name rather than by path, so one agent client configuration works on any machine holding that project. The workspace is the central place to manage them all: read a memory, record into it, see what each holds and which file holds it, and run SQL against its record — a read is unrestricted, a write may touch only the statements themselves and is reindexed afterwards. The four memory tools an agent already had are unchanged, and the workspace, the agent surface, and the command line all reach the same records through the one process. **This is the form to install.** | You want an agent to carry memory across sessions and you also want to read, check, and repair that memory yourself, with each project's memory isolated in its own repository and a shared one for what applies everywhere. |

### The retired stdio memory server

- `memory-ultra-rag-mcp-server` is no longer a member; `memory-rag` supersedes it.
  - Its repository is kept, so a machine with it installed keeps working.
  - `memory-rag` reads and writes the same `.memory-rag` directory and the same `memory/default` scope, so the account's settings directory, the environment prefix, the model cache, the scope directory names, and the SQLite schema stay as they are.
  - A memory written by the retired server stays readable by `memory-rag`, which is why its storage contract is unchanged.

### The two apps, and how they differ

- `research-rag` is a research app rather than a bare stdio server.
  - It is one process per project that serves a browser workspace, an agent surface, and a command line on one loopback port, and the attached agents can be listed and disconnected.
- `memory-rag` is a memory app, and it differs from `research-rag` in one deliberate way.
  - There is one process for the account rather than one per project, because a memory has a scope every project shares.
  - A command center that had to be visited once per repository would not be a central place for anything.

The projects are independently installable and versioned. Follow the README inside the submodule you pick for installation, configuration, and usage. Servers that are designed but not built are in [`TODO.md`](TODO.md); the parked graph memory server is one of them.

## What each app owns

- The workspace, the settings layer, and the vanilla gateway were three shared libraries. Each app now carries its own copy, and each copy is its app's code.
  - The workspace is the basic local evidence workspace, loopback HTTP host, request safety checks, and adapter contract: opt-in filters and panels for a host that supports them, a memory view for a host that serves memory instead of a corpus, an attached-clients panel, and a SQL console.
  - The settings layer holds the registry type, the merge that wins per key, the coercion every layer shares, the provenance each effective value carries, and the three path helpers that place a layer, and no keys, no `default.toml`, and no directory names of its own.
  - The gateway is the stdio MCP server that proxies UltraRAG's own Vanilla RAG stages, and only `research-rag` carries it, because only `research-rag` reaches UltraRAG.
  - Two copies of the workspace and the settings layer is duplication the collection accepts: an app that resolves a dependency on another project cannot fix what it ships, and a fix to either has to reach both.

## Clone the complete collection

```bash
git clone --recurse-submodules https://github.com/AhmedKishki/ultra-rag-mcp-servers.git
cd ultra-rag-mcp-servers
```

If you already cloned without submodules, initialize them with:

```bash
git submodule update --init --recursive
```

## Pull collection updates

```bash
git pull --ff-only
git submodule update --init --recursive
```

The parent repository deliberately pins each submodule to an exact commit. Updating the parent therefore reproduces the selected server versions instead of silently taking newer child commits.

## Work on one server

Treat each submodule as its own project. Commit and push changes from inside that server first. Then record the new child commit in this collection:

```bash
git -C research-rag switch main
git -C research-rag pull --ff-only origin main
git add research-rag
git commit -m "Update research-rag"
git push
```

- Use the equivalent commands for another server when updating its pinned revision.
- Update a shared library in its own repository first when changing it, then update every tested consumer's dependency pin before recording the submodule pointers here.
- Two servers may pin different commits of the same library, and that skew is allowed.
  - What would break the rule that each server is independently installable is a floating or vendored dependency.

## Stop stray server processes

A stdio MCP server belongs to the client that started it, so it cannot be reloaded or stopped from here: the client owns that process. The retired stdio memory server and the vanilla gateway it owned are the reason `scripts/stop-servers.sh` exists, and each of them started its children in its own session, so a process-group kill from a launcher cannot reach them. A client reload leaves that whole family behind.

The two apps are stopped from their own terminal, and each one records what it owns:

```bash
research-rag --project-root /path/to/project stop
memory-rag stop
```

Closing the terminal that started an app stops it as well. `stop` is therefore per product and per project, and it is the answer for a machine that is being worked on normally. It is not the answer for a machine whose client has reloaded and left a family behind, so `scripts/stop-servers.sh` still covers every product in this collection, the retired one included.

`scripts/stop-servers.sh` identifies those processes by the program each one runs, walks each family down to the UltraRAG children, and stops them by explicit PID — `SIGTERM` first, `SIGKILL` only for what ignores it. It never uses a pattern kill.

```bash
scripts/stop-servers.sh --dry-run            # list what it would stop
scripts/stop-servers.sh                      # stop every family it recognises
scripts/stop-servers.sh --project /path/to/project
scripts/stop-servers.sh --timeout 30         # seconds to wait before SIGKILL
```

- It reports each process with its role (`ui`, `server`, `gateway`, or `ultrarag`) and its depth below the server that owns it.
- It matches a product name only where a program can stand: the command itself, or the script a kernel ran after its interpreter, and a name that must be a file that is there and runnable. A product name in an editor's argument or a grep pattern is not a process.
- It exits non-zero if anything survived.
