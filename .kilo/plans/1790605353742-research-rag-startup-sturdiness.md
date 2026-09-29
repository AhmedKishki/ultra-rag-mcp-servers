# Research-rag startup sturdiness

## Goal

A first-run install and every later start either work or say exactly what is wrong, with no
session of forensics between the user and the cause.

The failure this came from: a stray `servers/memory/src/__pycache__/memory.cpython-311.pyc` in
the verified UltraRAG snapshot made `vanilla-ultra-rag-mcp` exit 2 on every start. The research
server surfaced nothing, the MCP client reported `Connection closed`, and the real message sat
unread in `logs/vanilla-gateway-stderr.log` fifteen times. Two contributing gaps: nothing checks
any dependency before the first tool call, and nothing tells a caller which dependency is at
fault.

## Decisions

1. **One dependency-check implementation, two consumers.** A new `health.py` produces the report;
   the `status` tool and a new `doctor` command read it, so they cannot disagree.
2. **`blocked_by` in the lean `status` answer, present only when unhealthy**, beside a `degraded`
   list for conditions that reduce quality rather than block. Both absent when healthy, so the
   healthy answer does not widen. This follows the existing `hybrid_ready: false` beside
   `generation_upgrade_required` precedent.
3. **The doctor never writes a client entry.** It prints the exact block and validates whatever
   entry the user points it at.
4. **Every repair is an explicit flag.** No repair is the default; no flag implies another.
5. **Both repositories change.** The vanilla changes are runtime-integrity fixes that stand on
   their own; research degrades to `unknown` against the older pinned vanilla so either release
   can ship first.
6. **`install_managed_runtime` leaves the verified tree read-only** and prints the undo command.

## What the plan must not break

From `research-ultra-rag-mcp-server/AGENTS.md`:

- The stdio handshake stays independent of work no tool asked for. No health check may start the
  gateway; `tests/test_integration.py` pins this with a gateway that exits immediately. Every
  check in `health.py` is a read.
- `Never add research behavior to the vanilla repository to support this project.` The two
  vanilla items below are about the runtime's own integrity, which is vanilla's own concern.
- `Keep model downloads lazy.` Prefetching is an operator flag, never server behaviour.
- `Answer through the core`: the doctor and `status` call the same `ResearchService`-level code,
  and the `research://status` resource projection stays identical to the tool.

## Task 1 — `health.py`, the shared check

New `src/research_ultra_rag_mcp/health.py`. One function returning named checks, each
`{state: ok | warn | blocked | unknown, reason, remedy_command}`. No gateway process, no network,
no writes. Run off the event loop; cache the result per process, keyed on the runtime root
marker's `(mtime, size)`, because the tree hash reads 11 MB.

| Check | Reads | blocked | warn |
|---|---|---|---|
| `project_identity` | `project.json` vs the runtime root marker | marker names another `project_id`, or a non-empty unmarked root | — |
| `runtime_root` | absolute, is a directory, writable | unwritable or not a directory | — |
| `vanilla_runtime` | `validate_managed_runtime` from the pinned vanilla package | tree hash mismatch (with the offending path when the newer vanilla names it) | snapshot absent and `--offline` forbids the download |
| `models` | pinned tables in `embeddings.py` / `rerankers.py` against `model_cache_root` | absent under `--offline` | absent online: the first ingest/search downloads it |
| `lock` | `project.lock` owner pid and start time | — | another process holds it: write calls are rejected |
| `generation` | `status.py` | no generation at all | stale generation, or a `generation_upgrade_required` |
| `capacity` | free space on the state root's filesystem, `retained_generation_bytes` | below the space the current build needs | approaching it |
| `code_currency` | `version.restart_required` | — | running server predates the installed code |

Reuse the root-claim checks `resolve_config` already performs; extract them rather than
reimplement. `unknown` means *not checked* (older vanilla, or a check that could not run) and
must never read as healthy — the doctor names which check did not run.

## Task 2 — the tool error names the cause

In `ultrarag.py`, when the vanilla client fails to start or exits while initializing, read the
tail of the logs the transport already writes — `<logs_root>/vanilla-gateway-stderr.log` and
`<workspace>/logs/<namespace>-child-stderr.log` — and raise a `ToolError` carrying what failed,
the last meaningful lines, and both paths. A gateway that cannot start is still reported by the
tool that needed it; only the message improves.

Also in `ultrarag.py`: a call that exceeds the transport timeout names the namespace that was
busy and where its log is, instead of reporting a bare timeout. No process-tree inspection.

Tests: the existing integration stub that exits immediately also asserts the surfaced text; a
case where the log file is absent still produces a usable message.

## Task 3 — `blocked_by` and `degraded` on `status`

In `tool_views.py`, add `blocked_by` (a list of `{check, reason, remedy}`) and `degraded`, both
omitted when empty. The full payload carries the same facts plus the complete per-check detail,
per the rule that the lean answer and the service payload describe the same things.

Amend the lean-projection rule in `AGENTS.md` to record the precedent and the bound: disclose a
condition only when the caller must act on it.

Tests: update the pinned key set in `tests/test_tool_views.py:194`; both fields absent when
healthy; present with a cause and a remedy when not; `research://status` unchanged.

## Task 4 — vanilla: the message names the file

`vanilla_ultra_rag_mcp/runtime.py`. `validate_managed_runtime` reports the first differing path —
unexpected file, missing file, or changed file — with the observed mode for an unexpected file,
alongside the two hashes. Same exit code, same advice, one more sentence.

Test: a tree polluted with a single extra file names that file. This is the highest-value line in
the plan; it is what turned today's half-hour into a guess.

## Task 5 — vanilla: install leaves the tree read-only

`install_managed_runtime` chmods the verified tree to `0555` directories and `0444` files after
the rename into place, and prints the single undo command to stderr. Guard the permission call
for platforms without POSIX modes and skip with a note there. Validation stays read-only, so a
read-only tree still passes. Add the rule text to vanilla's `AGENTS.md` beside the existing
"Prevent Python bytecode from being written into the verified runtime" (line 89).

Tests: an installed tree is not writable; `vanilla-ultra-rag-runtime --offline` passes against it;
an extra-file pollution is still detected; the mode is reported on a non-POSIX platform.

## Task 6 — `research-ultra-rag doctor`

A subcommand beside the existing `create`/`refresh`/`find`/`context`/`change`.

- **Default: read-only.** One line per check, state, reason, remedy command. Exit 0 when nothing
  is blocked, 1 when something is, 2 on a usage error.
- `--mcp-entry` prints the exact JSONC block for the resolved config, consistent with
  `kilo-mcp.example.jsonc`.
- `--check-entry <path>` validates a client entry: the executable exists, the paths match the
  resolved config, the timeout is sane, and no second entry names the same project root. Reports
  only.
- `--prefetch-models` (network) loads the pinned embedding and reranker models into the
  configured cache and reports what it fetched.
- `--repair-runtime` (network) moves a hash-mismatched tree to
  `<cache>/quarantine/<commit>-<observed-hash-prefix>` — never deletes it — installs fresh, and
  re-validates. This automates the advice the error already gives and keeps the evidence.
- Servers found for this project root are reported with the existing stop command named, not a
  second kill path.

## Task 7 — documentation

| File | Change |
|---|---|
| research `README.md` | a "Check the installation" section under *Install once*; troubleshooting entries for `Connection closed`/gateway start failure, each `blocked_by` value, a missing reranker degrading to `rerank_fallback`, duplicate servers for one root, and `restart_required` |
| research `FEATURES.md` | the doctor command and the health disclosure as shipped capabilities |
| research `AGENTS.md` | the lean-projection amendment; `health.py` in the repository map; the rules that the doctor never writes a client entry and never downloads without a flag |
| research `AGENT_GUIDE.md` | what an agent does with `blocked_by` (act on the remedy, do not retry) and that `degraded` is expected when a model is deliberately absent |
| vanilla `README.md` | an installed tree is read-only, and the undo command; the mismatch message names the file |
| collection `README.md` | the doctor alongside "Stop stray server processes" |

Markdown states the present, never the past: no change log, no before/after narrative.

## Validation

```bash
# research
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
uv run python -m compileall -q src tests

# vanilla
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
```

Vanilla's runtime rule also applies: test a fresh managed cache, then validate it with
`vanilla-ultra-rag-runtime --offline`.

No `scripts/evaluate_retrieval.py` run and no `MEASUREMENTS.md` retrieval change. Nothing here
touches the index, the ranking, the chunker, or the corpus; that harness is bound to a
retrieval-quality claim. The one number to record is the added `status` latency from the one-time
tree read, which belongs in `MEASUREMENTS.md` beside the other cost figures.

## Risks

- **`status` gains an 11 MB read.** Cached per process, keyed on the marker. If the measured
  cost is unacceptable, drop `vanilla_runtime` from the lean path and leave it to the doctor.
- **A read-only install blocks a dev workflow** that points `ULTRARAG_ROOT` at the installed
  tree. The undo command is printed at install and documented; this is a deliberate trade for
  protection that no operator has to remember.
- **`unknown` must not read as healthy.** A caller that treats "not checked" as "fine" is worse
  than the current silence, so the doctor names the check that did not run.
- **`degraded` invites pointless repair.** The agent guide states that a reranker fallback is
  expected when the model is deliberately absent, so an agent does not try to "fix" it.
- **Duplicate servers for one project root stay legal.** The doctor reports them; the
  concurrency model is unchanged, because two search-only servers are not a conflict.

## Out of scope

- The memory-rag server, including the `ULTRARAG_CHECKOUT` guard against a managed cache and the
  reference-file import that most likely wrote the file. It is the follow-up that generalises
  tasks 2 and 4, and it is a separate repository.
- Collapsing the process tree, dropping the snapshot hash, or inlining BM25. Each breaks the
  contract that UltraRAG is reused unmodified.
- Automatic generation pruning. The doctor reports retained bytes and free space; it never
  deletes an index.
- Remote or HTTP transport, authentication, multi-user deployment.
- Publishing to PyPI, or a true `uvx`/`npx` path. The honest comparison is that a local service
  with model weights and an index cannot be a single ephemeral artifact, and the plan targets the
  part that can match: one command that gets a new machine to a working, diagnosable state.

## Release order

1. `vanilla-ultra-rag-mcp-server`: tasks 4 and 5, its own gates, commit, push, tag.
2. `research-ultra-rag-mcp-server`: pin the new vanilla commit, then tasks 1, 2, 3, 6, 7 with the
   research gates, commit, push.
3. `ultra-rag-mcp-servers`: update the vanilla submodule pointer, then the research pointer, each
   only after its child commit is on its remote.

Each phase reverts on its own: the vanilla items are a release, and the two new status fields are
additive.
