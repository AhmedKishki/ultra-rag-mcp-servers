# UltraRAG MCP servers

This repository is the collection point for independent MCP servers built around UltraRAG and their reusable local UI library. Each project lives in its own Git repository and is included here as a Git submodule pinned to a specific, tested commit.

## Credit to UltraRAG

The MCP servers are directly based on [`OpenBMB/UltraRAG`](https://github.com/OpenBMB/UltraRAG). UltraRAG's upstream team describes it as a joint project of [`THUNLP`](https://nlp.csai.tsinghua.edu.cn/) at Tsinghua University, [`NEUIR`](https://neuir.github.io/) at Northeastern University, [`OpenBMB`](https://www.openbmb.cn/home), and [`AI9stars`](https://github.com/AI9Stars), together with the [`UltraRAG contributors`](https://github.com/OpenBMB/UltraRAG/graphs/contributors). Their work provides the MCP architecture and RAG implementation underlying this collection.

UltraRAG is licensed under the [`Apache License 2.0`](https://github.com/OpenBMB/UltraRAG/blob/main/LICENSE.txt). These are independent projects, not official UltraRAG releases, and are not affiliated with or endorsed by the upstream organizations. See [`NOTICE`](NOTICE) and the notice inside each server repository for version-specific attribution.

## Included servers

This README is the collection-level comparison and selection guide. Each server's own README is a standalone user manual for that server and does not compare it with the other projects in this collection.

| Server | What it is | Pick it when |
|---|---|---|
| [`vanilla-ultra-rag-mcp-server`](vanilla-ultra-rag-mcp-server/) | A thin gateway exposing UltraRAG's own Vanilla RAG stages: retrieval, RAG prompt, generation, extraction, and evaluation. | You want UltraRAG itself, unmodified, behind an MCP interface. |
| [`research-ultra-rag-mcp-server`](research-ultra-rag-mcp-server/) | A research knowledge base over your own PDF and EPUB collection: isolated per project, hybrid BM25 plus dense retrieval, metadata, provenance, original-file locators, reversible source exclusions, reviewable metadata with project, branch, and keyword filter layers, per-query source selection, and a local evidence UI. | You need to find, narrow, and cite evidence in a document collection, at the scale of tens to low hundreds of sources on a CPU. |
| [`memory-ultra-rag-mcp-server`](memory-ultra-rag-mcp-server/) | UltraRAG's own memory served over stdio MCP in two kinds: **global memory**, one per user, and **local memory**, one per project. Each kind is a standing `MEMORY.md` plus one dated dialogue file per day, written by the pinned UltraRAG server running as a child process, so the tools, the parameters, the file names, and the format are upstream's. Four tools: `get_global_memory`, `save_memory`, `get_local_memory`, `save_local_memory`. The storage root is passed in, so the memory lands where a UltraRAG UI reads it and the UI shows the same memory an agent writes. | You want the memory UltraRAG itself keeps, per user and per project, exposed to an agent and visible in the UltraRAG UI. |
| [`graph-memory-ultra-rag-mcp-server`](graph-memory-ultra-rag-mcp-server/) | **Parked 2026-09-22.** A project-scoped, strongly typed store of objects, relations as addressable atoms, and atomic statements for durable operational memory between agent sessions: the MCP reference memory server's model reimplemented in Python, extended with a project-declared type schema in `project-types.json`, a canonical vocabulary seeded at initialization, a bounded read surface with no whole-store read, admission control that refuses an exact duplicate and records a reasoned override, reversible withdrawal, addressed relations, one separate global store per user, and promotion across that line behind an explicit `scope`. | Not yet: the project is kept for later while its definition is revised, so the collection's supported memory server is `memory-ultra-rag-mcp-server`. |

The servers are independently installable and versioned. Follow the README inside the submodule you pick for installation, MCP client configuration, and usage.

## Shared local interface

[`ui-ultra-rag-mcp`](ui-ultra-rag-mcp/) contains the basic local evidence workspace, loopback HTTP host, request safety checks, and adapter contract, including opt-in source-selection, category-partition, and project-tag filters for servers that support them. It is a library, not an MCP server and not a knowledge base. A server can pin it as a dependency and retain only a thin adapter for its own tools and project policy. The research server currently uses it; future document-oriented servers can reuse it without sharing indexes or project data.

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
git -C research-ultra-rag-mcp-server switch main
git -C research-ultra-rag-mcp-server pull --ff-only origin main
git add research-ultra-rag-mcp-server
git commit -m "Update research MCP server"
git push
```

Use the equivalent commands for another server when updating its pinned revision. Update `ui-ultra-rag-mcp` in its own repository first when changing the shared interface, then update every tested consumer's dependency pin before recording the submodule pointers here.
