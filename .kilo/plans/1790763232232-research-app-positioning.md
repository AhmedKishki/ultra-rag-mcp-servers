# research-rag: a standalone research app with a browser workspace and an agent surface

Status: in progress. Revised after the user reversed this plan's central decision.

## What changed and why

The first pass removed the MCP surface. That was wrong. The app is not a browser-only
product that happens to have inherited a server; it is a server product that also has a
browser. The user's description: `research-rag` is a repackaging of
`research-ultra-rag-mcp-server` as a stand-alone installed project, and one app controls
a single instance and can connect and disconnect MCP clients, with the UI and the CLI as
its control surfaces.

Consequences, all of which reverse work already landed:

- The agent surface comes back with the same capability the MCP server has today: the
  seven operations and the two resources. "Same functionality as currently exists" is
  the requirement, and the tools are the functionality.
- The lean/full answer projection comes back. It is the reason an agent's answer is
  10.8 kB instead of 19.8 kB, and `MEASUREMENTS.md` already carries those figures. A
  product with agents cannot justify deleting the only lever aimed at agent tokens.
- One app process owns one project, rather than one process per front end. The UI and
  the CLI become front ends to that instance.

Kept from the first pass, because it is correct independent of the reversal: the four
pinned legacy names and their guard test, the distinct launcher names and state files,
the launcher argument-order fix, the process-sweep token fix, the real-launcher
integration test, the port claim, `STORAGE.md`, and the rewritten architecture test.

## Architecture

One app process per project. One loopback port. That port carries everything.

```
MCP client ── streamable HTTP ─┐
                              ├── research-rag (one process, one project lock)
browser workspace ── HTTP ────┤     ├── ResearchService
                              │     ├── project and source policy
research-rag (CLI) ── control ┤     ├── extraction, metadata, provenance
                              │     ├── immutable generations
research-rag mcp ── stdio ────┘     ├── hybrid retrieval with reranking
  (bridge to /mcp)                    └── stdio MCP ──> vanilla-ultra-rag-mcp
```

One process, one gateway child, one project lock. The workspace is hosted by the app, so
its adapter calls the service in process. The CLI reaches the same instance over a
loopback control API rather than constructing a second service. An agent reaches it at
`/mcp`, or through a stdio bridge for a client that speaks only stdio.

The vanilla gateway stays a pinned dependency. The user described this as a
repackaging, and the gateway is a separately released member of the collection with its
own history, so absorbing it would be a different and much larger change.

## Package layout

The domain core is untouched. The restructure is the surface layer, moved under
`surfaces/` so the boundary the architecture test enforces is a directory rather than a
list of filenames.

```
src/research_rag/
  app.py          the running app: lifecycle, port, surfaces, client registry
  control.py      the loopback control API the CLI and the UI's client list talk to
  bridge.py       `research-rag mcp`: stdio to the app's /mcp endpoint
  service.py      ResearchService
  <engine>        config, sources, extraction, generation, ingestion, search,
                  status, review, dense, rerankers, embeddings, settings,
                  storage, launcher, health, doctor, ultrarag, version
  surfaces/
    mcp.py        the seven operations, the two resources, the lean/full projection
    cli.py        the command centre
    ui.py         the workspace profile, its adapter, and the port claim
```

## Operations on the app

| Command | Effect |
|---|---|
| `start` | bring the app up on a claimed port, and print its URL and MCP endpoint |
| `stop` | stop the app and what it started; `stop --servers` also ends a stray build |
| `status` | the app's state, and whether it is running |
| `clients` | the MCP clients attached to this app |
| `disconnect <id>` | drop one attached client |
| `ui` | open the workspace in a browser against the running app |
| `search`, `sources`, `passage`, `ingest`, `include`, `exclude`, `metadata` | corpus work, through the running app |
| `config`, `doctor` | local reads, in process, never starting the app |

`config` and `doctor` read local state and open no gateway, so they must not start a
daemon. `stop` must never start one. Everything else ensures the app is running and talks
to it, which is what "one app controls a single instance" means in practice.

## Tasks

1. Restore the agent surface under `surfaces/mcp.py`: the seven operations, the two
   resources, the lean/full projection, the instructions, and the per-session detail
   setting that was made inert in the first pass.
2. Build `app.py`: resolve the project, claim the port, own the gateway and the service,
   mount the workspace and the MCP endpoint on one port, track attached MCP clients, and
   answer health.
3. Build `control.py`: the loopback, same-origin control API the CLI speaks.
4. Build `bridge.py`: `research-rag mcp` as a stdio proxy to the app's `/mcp`.
5. Build `surfaces/cli.py` as the command centre, with the operations above, and move
   `ui.py` under `surfaces/`.
6. Restore `tool_detail` as a real setting in `settings.py` and `default.toml`, and drop
   the inert note and its assertion from `test_data_roots.py`.
7. Restate `test_architecture.py` for the new layout: the engine imports neither the web
   stack nor FastMCP, and no engine module imports `surfaces/`.
8. Tests: the projection, the app lifecycle and port claim, the control API, the client
   registry and a forced detach, the stdio bridge against the real app, and the retained
   real-launcher integration test.
9. Documents: `AGENTS.md`, `README.md`, `FEATURES.md`, `MEASUREMENTS.md`, `TODO.md` for a
   product that is a server with three front ends rather than a workspace with one.
10. Validate on 3.11 and 3.12, then the acid test: the real project, an MCP session over
    `/mcp`, a second session over the stdio bridge, the workspace in a browser, and the
    CLI reaching the same instance.

## Rules that survive the reversal

- The user settings directory, the settings environment prefix, the model cache, and the
  launcher state files keep their names while both products exist. `tests/test_data_roots.py`
  states each one and why, and a rename is a migration.
- The on-disk contract is byte-compatible with `research-ultra-rag-mcp`, so both products
  may serve one project while the migration runs. The app's launcher and the server's
  coexist, and neither may signal the other's processes.
- One answer shape per operation, plus the lean projection for an agent. The workspace
  requests the full payload and the CLI prints it; an agent gets the projection, and the
  two cannot be served by different code paths over different data.
- Retrieval is the engine's decision, not a caller's. The agent surface offers no mode,
  no detail, and no chunk tuning, exactly as the CLI does not.
- The workspace stays on loopback, and the MCP endpoint with it.
