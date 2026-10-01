# UltraRAG MCP servers

This repository is the collection point for independent MCP servers built around UltraRAG and the two libraries they share. Each project lives in its own Git repository and is included here as a Git submodule pinned to a specific, tested commit.

## Credit to UltraRAG

The MCP servers are directly based on [`OpenBMB/UltraRAG`](https://github.com/OpenBMB/UltraRAG). UltraRAG's upstream team describes it as a joint project of [`THUNLP`](https://nlp.csai.tsinghua.edu.cn/) at Tsinghua University, [`NEUIR`](https://neuir.github.io/) at Northeastern University, [`OpenBMB`](https://www.openbmb.cn/home), and [`AI9stars`](https://github.com/AI9Stars), together with the [`UltraRAG contributors`](https://github.com/OpenBMB/UltraRAG/graphs/contributors). Their work provides the MCP architecture and RAG implementation underlying this collection.

UltraRAG is licensed under the [`Apache License 2.0`](https://github.com/OpenBMB/UltraRAG/blob/main/LICENSE.txt). These are independent projects, not official UltraRAG releases, and are not affiliated with or endorsed by the upstream organizations. See [`NOTICE`](NOTICE) and the notice inside each server repository for version-specific attribution.

## Included projects

This README is the collection-level comparison and selection guide. Each server's own README is a standalone user manual for that server and does not compare it with the other projects in this collection.

| Project | What it is | Pick it when |
|---|---|---|
| [`vanilla-ultra-rag-mcp-server`](vanilla-ultra-rag-mcp-server/) | A thin gateway exposing UltraRAG's own Vanilla RAG stages: retrieval, RAG prompt, generation, extraction, and evaluation. | You want UltraRAG itself, unmodified, behind an MCP interface. |
| [`research-ultra-rag-mcp-server`](research-ultra-rag-mcp-server/) | **Frozen.** A research knowledge base over your own PDF and EPUB collection: isolated per project, hybrid BM25 plus dense retrieval, metadata, provenance, original-file locators, reversible source exclusions, filter layers by project, branch, and keyword, a command line that creates, builds, queries, and reviews a project with no MCP client, and a local evidence UI. Kept for the machines that run it: it reads and writes the same projects as `research-rag` and will not be changed. | You already run it, and you want it to stay exactly as it is. For anything new, use `research-rag`. |
| [`research-rag`](research-rag/) | A research knowledge base over your own PDF and EPUB collection, as an installed application: one process per project serving a browser workspace, an MCP agent surface, and a command line on one loopback port. The engine, the storage layout, and the seven agent operations are the ones the frozen server serves, plus a stdio bridge for a client that cannot open a socket, which takes a project name rather than a path so one entry works on any machine holding that project. **This is the form to install and the only one that changes.** | You want to find, narrow, and cite evidence in a document collection, at the scale of tens to low hundreds of sources on a CPU, and you read it in a browser, drive it from a terminal, or hand it to an agent. |
| [`memory-ultra-rag-mcp-server`](memory-ultra-rag-mcp-server/) | **Frozen.** UltraRAG's memory over stdio MCP, extended with two scopes: **local**, kept in the project repository under `.memory-rag` so it travels with the project, and **global**, under a storage root that every project on the account shares. Each is a SQLite file holding the statements, the kind each is filed under, its place, and when it was added and how often it has been recalled, and a vector each, with `MEMORY.md` available as a plain-prose rendering written when it is asked for and never read back as the record. Four tools — `record_memory`, `recall_memory`, `forget_memory`, and `record_handoff` — with the memory chosen by a `scope` argument that defaults to the project, and no user identifier, because a server is bound to one project and reaches exactly two memories. A recall searches both memories and ranks the results together, so one question gets one answer and every statement says which memory it is in; forgetting matches the exact text a recall returned and removes nothing when that text is ambiguous. No API is used. Kept for the machines that run it: it reads and writes the same memories as `memory-rag` and will not be changed. | You already run it, and you want it to stay exactly as it is. For anything new, use `memory-rag`. |
| [`memory-rag`](memory-rag/) | The account's global memory and every registered project's local memory, as an installed application: **one** process holding them all and serving a browser workspace, an MCP agent surface, and a command line on one loopback port. A project is registered by name rather than by path, so one agent client configuration works on any machine holding that project. The workspace is the central place to manage them all: read a memory, record into it, see what each holds and which file holds it, and run SQL against its record — a read is unrestricted, a write may touch only the statements themselves and is reindexed afterwards. The four memory tools an agent already had are unchanged, and the workspace, the agent surface, and the command line all reach the same records through the one process. **This is the form to install and the only one that changes.** | You want an agent to carry memory across sessions and you also want to read, check, and repair that memory yourself, with each project's memory isolated in its own repository and a shared one for what applies everywhere. |

### Why the frozen servers stay

- `research-ultra-rag-mcp-server` stays in this collection as a submodule because the machines that run it read and write the same project layout as the app.
  - A project those machines still open is a project the app must not make unreadable.
  - That is why the on-disk contract is frozen on both sides, and it is a compatibility constraint rather than a reason to prefer the server.
  - A new project gets `research-rag`; the server is kept, not offered.
- `memory-ultra-rag-mcp-server` stays for the same reason and by the same argument.
  - It reads and writes the same `.memory-rag` directory and the same `memory/default` scope that `memory-rag` serves.
  - Copies of it are running on machines where those memories hold real statements, so the account's settings directory, the environment prefix, the model cache, the scope directory names, and the SQLite schema are all fixed while it is installed.
  - A new memory project gets `memory-rag`; the server is kept, not offered.

### The two apps, and how they differ

- `research-rag` is a research app rather than a bare stdio server.
  - It is one process per project that serves a browser workspace, an agent surface, and a command line on one loopback port, and the attached agents can be listed and disconnected.
  - It is the form to install, and it is the only one of the two research products that changes.
- `memory-rag` is a memory app, and it differs from `research-rag` in one deliberate way.
  - There is one process for the account rather than one per project, because a memory has a scope every project shares.
  - A command center that had to be visited once per repository would not be a central place for anything.

The projects are independently installable and versioned. Follow the README inside the submodule you pick for installation, configuration, and usage. Servers that are designed but not built are in [`TODO.md`](TODO.md); the parked graph memory server is one of them.

## Shared libraries

- [`ui-ultra-rag-mcp`](ui-ultra-rag-mcp/) is the basic local evidence workspace, loopback HTTP host, request safety checks, and adapter contract.
  - Its opt-in filters and panels: source-selection, category-partition, and project-tag filters for servers that support them; a memory view for a server that serves memory instead of a corpus; an attached-clients panel for a host that is a server and can therefore report which agents are connected to it; and a SQL console for a host that wants its own stored records readable and editable from a browser.
  - It is a library, not an MCP server and not a knowledge base.
  - A server can pin it as a dependency and retain only a thin adapter for its own tools and project policy.
  - The research app, the research server, the memory app, and the memory server use it; future document-oriented projects can reuse it without sharing indexes or project data.
- [`config-ultra-rag-mcp`](config-ultra-rag-mcp/) is the configuration layering both servers resolve before they do any work.
  - It holds the registry type, the merge that wins per key, the coercion every layer shares, the provenance each effective value carries, and the three path helpers that place a layer.
  - It is a library, not an MCP server, and it holds no keys, no `default.toml`, and no directory names of its own: a server declares its own tunables and passes its own account, project, and package names in, which is how two servers that classify their settings differently share one implementation.
  - The research app, the research server, the memory app, and the memory server pin it, at different commits today, and each keeps its own registry, its own packaged defaults, and its own error type its callers catch.

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

A stdio MCP server belongs to the client that started it, so it cannot be reloaded or stopped from here: the client owns that process. Each server in turn owns a vanilla UltraRAG gateway and, through it, UltraRAG's corpus and retriever children, and every stdio child is started in its own session, so a process-group kill from a launcher cannot reach it. A client that reloads its servers can therefore leave a whole family behind.

`scripts/stop-servers.sh` identifies those processes by their own entry points, walks each family from its server down to the UltraRAG children, and stops them by explicit PID — `SIGTERM` first, `SIGKILL` only for what ignores it. It never uses a pattern kill.

```bash
scripts/stop-servers.sh --dry-run            # list what it would stop
scripts/stop-servers.sh                      # stop every family it recognises
scripts/stop-servers.sh --project /path/to/project
scripts/stop-servers.sh --timeout 30         # seconds to wait before SIGKILL
```

- It reports each process with its role (`ui`, `server`, `gateway`, `ultrarag`, `verify`) and its depth below the server that owns it.
- It exits non-zero if anything survived.
- Stopping a server is not the same as restarting it.
  - The client owns that process, so bring it back from your MCP client.
  - A browser UI the server hosts on `--ui-port` returns with it.
