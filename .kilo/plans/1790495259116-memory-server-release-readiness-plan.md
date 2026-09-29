# Publish the typed memory store as the collection's memory server

**Goal:** make `memory-ultra-rag-mcp-server`'s typed-store line the published server, verified and documented honestly, and remove `graph-memory-ultra-rag-mcp-server` from the collection.

## Context

One local repository holds two unrelated histories:

- `origin/main` = `bd7bbef` — the published wrapper: four tools over UltraRAG's `MEMORY.md` plus dated rounds, version 0.3.0, with a browser view. The collection's submodule pointer sits here, and the collection README describes this product.
- local `main` = `e9c84f2` — 25 commits, no shared ancestor, **never pushed**: the project-scoped, strongly typed SQLite/FTS5 store. Twenty tools, the two-store model, admission control, bounded reads, 264 tests, three CI workflows, thirteen ADRs. Version 0.1.0, `Development Status :: 2 - Pre-Alpha`.

The working tree is checked out detached at `bd7bbef`, so reading files there shows the old product, not the code under development. Every fact in this plan about the new line comes from `git show main:<path>`.

The new line's `AGENTS.md` documentation discipline requires `README.md`, `features.md`, and `AGENT_GUIDE.md` to agree on what is available; the release checklist in `TODO.md` is entirely unchecked; and no gate in it has ever run in CI, because the code has never left this machine.

## Decisions (settled with the user)

1. **The new line becomes `main`.** The old tip is preserved as a branch, `legacy/ultrarag-wrapper`, pushed before `main` moves, so its history stays reachable.
2. **Version continues at 0.4.0** with `Development Status :: 3 - Alpha`, published only after CI is green on CPython 3.11 and 3.12 and the compatibility oracle has run on this code. No git tag and no GitHub Release: no sibling repository has either, and installation is `git clone` plus `uv sync --frozen`.
3. **Scope is release readiness only.** Multi-hop relation path search, session/durable tiers, operative rules, approval states, modifiers, counters, export/import, the Markdown view, the `verify` command, and the browser view stay recorded in the child's `TODO.md` and `architecture.md` as they already are.
4. **`graph-memory-ultra-rag-mcp-server` is unwired from the collection and its GitHub repository is archived** (reversible). It is not deleted. Nothing in the new memory line references it; the archived wrapper branch's link to it keeps resolving.

### What the new server is, for the docs that must say it

It is **not** UltraRAG's memory improved. UltraRAG's built-in memory is two tools (`get_global_memory`, `save_memory`) over one free-text `MEMORY.md` per user, with no search, no scoping, no types, and no removal. The new server adopts the **MCP reference memory server's** model — entities, relations, atomic observations — eight of whose nine tools it ports verbatim, and adds: one store per project plus one global store per user with `scope` on every write and removal; a declared type schema that refuses an undeclared type; a bounded read surface with `read_graph` withdrawn; admission control that refuses an exact duplicate with what it conflicts with and records a reasoned override; reversible withdrawal with a reason; relations as addressable objects; a canonical research vocabulary in one call; and identifiers that are never reused.

It deliberately **drops** byte compatibility with UltraRAG's `MEMORY.md` format and the browser view. An UltraRAG UI pointed at the same storage root would no longer show the same memory. The release notes and the collection README must state this, because it is the one thing a reader could otherwise get wrong.

## Document drift to correct (verified on `main`)

| File | Line / place | Now | Must become |
| --- | --- | --- | --- |
| `README.md` | 11 | "237 tests … exposes nineteen tools" | 264 tests; twenty tools (17 in `tools.py` + `list_projects`, `initialize_project`, `project_status` in `server.py`) |
| `README.md` | 60-61 (facet table) | "Free text today; declared and enforced in M1b" | declared and enforced; M1b landed |
| `README.md` | status paragraph | "The remaining milestones … are not implemented" above a table marking M2 implemented | one statement that M1 through M2 landed and M3-M5 did not |
| `AGENTS.md` | Project status | "the server exposes nineteen tools" | twenty |
| `AGENT_GUIDE.md` | 5 | "implements milestones M1, M1a, M1b, M1c, and M1d" | M1, M1a-M1g, M2 |
| `AGENT_GUIDE.md` | Reading memory, `check_memory` | "read-only today; M1d adds the write path that consumes it" | M1d landed; `remember` consumes the verdict |
| `features.md` | Status line | "implements milestones M1, M1a, M1b, M1c, M1d, M1e, M1f, and M1g" | add M2, which the same file already marks implemented below |

While sweeping, re-check every occurrence of `nineteen`, `237`, `Free text today`, `0.1.0`, and `MEMORY.md` on the branch. Add a test that fails when the documented tool count differs from the registered count — the drift above survived precisely because nothing checks it.

## Tasks

### A. The child repository

1. **Move the worktree onto the new line and clear stale artifacts.**
   ```bash
   cd memory-ultra-rag-mcp-server
   git checkout main
   rm -rf dist src/memory_ultra_rag_mcp.egg-info src/memory_ultra_rag_mcp/__pycache__
   uv sync --frozen
   uv run --frozen python scripts/check_sqlite_fts5.py
   ```
   `.venv`, `dist/`, and `__pycache__` all belong to the old line (the old line depends on `ui-ultra-rag-mcp`; the new one does not). `uv sync --frozen` reconciles the environment.

2. **Run the release checklist as written in `TODO.md`, in this order, on CPython 3.11 and 3.12.**
   ```bash
   uv run --frozen ruff format --check .
   uv run --frozen ruff check .
   uv run --frozen pytest
   uv run --frozen pytest -q tests/test_performance.py   # quiet machine; this suite is timing-sensitive
   uv build
   ```
   Then the two opt-in suites. The oracle needs Node and the network; check `node --version` and `npx --version` first. If Node is absent, stop and report it rather than skipping silently — the release gate depends on it.
   ```bash
   MEMORY_ULTRA_RAG_MCP_ORACLE=1 uv run --frozen pytest -q tests/test_compat_oracle.py
   ```
   Record the oracle's outcome in `docs/audits/memory-reference-server-parity.md` (it is dated 2026-09-20 and predates M2's `scope` and `include_global` additions). If the oracle fails, fix or record it before publishing; that file is the evidence the ported contract still holds.

3. **Correct the drift table above and add the tool-count test.** Update `README.md`, `AGENTS.md`, `AGENT_GUIDE.md`, `features.md`. Keep `AGENT_GUIDE.md` and `src/memory_ultra_rag_mcp/instructions.py` equivalent, as the new line's own documentation discipline requires.

4. **Bump the release claim.** `pyproject.toml`: `version = "0.4.0"`, classifier `Development Status :: 3 - Alpha`, then `uv lock` so the lockfile's root version follows. Leave `required-version = ">=0.12,<0.13"` and the four pinned dependencies alone; ADR 0003 and ADR 0002 fix them.

5. **Re-run the gates after the edits** (steps 2's first five commands plus `uv build`), then commit one publication commit on `main` that records the supersession, the corrected numbers, the oracle result, and `Release 0.4.0.`

6. **Push in an order that cannot lose the old line.**
   ```bash
   git branch legacy/ultrarag-wrapper bd7bbef
   git push origin legacy/ultrarag-wrapper
   git push origin main:refs/heads/typed-store      # CI runs here first
   ```
   Wait for the three workflows to pass on `typed-store` (`quality-gates.yml` on 3.11 and 3.12, `platform-prerequisites.yml`, and the scheduled oracle if it fires). Only then move `main`:
   ```bash
   git push --force-with-lease=main:bd7bbef origin main:main
   git push origin --delete typed-store
   ```
   `--force-with-lease` with the explicit old SHA is required: the histories are unrelated, so this is a non-fast-forward, and an unpinned force push could clobber a concurrent push.

### B. The collection repository

7. **Remove `graph-memory-ultra-rag-mcp-server`.** The directory is empty (the submodule was never initialized), so this is index and metadata only.
   ```bash
   git rm --cached graph-memory-ultra-rag-mcp-server
   rmdir graph-memory-ultra-rag-mcp-server        # if the empty directory remains
   ```
   Edit `.gitmodules` to drop its stanza (lines 10-12). This is the one edit the parent's own rules caution about; the removal is the user's recorded decision, and the commit message should say so.

8. **Update the collection documents.**
   - `README.md` line 19: replace the wrapper row with the typed store — 20 tools, one store per project plus one global store per user, declared type schema, bounded read surface, admission control, relations as objects, the canonical vocabulary, and an explicit note that it is not UltraRAG's `MEMORY.md` format and has no browser view in this release. Keep the "You want …" selection column in the table's voice.
   - `README.md` line 20: delete the graph row.
   - `README.md` line 26: the sentence "The research server and the memory server currently use it" becomes false — the new memory server does not depend on `ui-ultra-rag-mcp` at all. Keep the UI paragraph's description of the memory capability, but state that no server in the collection uses it now and that the memory server's own view is deferred work.
   - `AGENTS.md` line 8: drop the `(parked)` list entry; line 35: drop its validation command.
   - `TODO.md` needs no entry: the child's own roadmap covers the deferred features, and the parent's rule is for collection-level work.

9. **Point the collection at the published child, then validate and commit.**
   ```bash
   git submodule update --init --recursive memory-ultra-rag-mcp-server
   git add memory-ultra-rag-mcp-server
   git add .gitmodules AGENTS.md README.md
   git diff --check
   git submodule status --recursive
   git -C memory-ultra-rag-mcp-server status --short --branch
   git diff --check
   git commit -m "Point memory-ultra-rag-mcp-server at the typed store and drop graph-memory" 
   git push origin main
   ```
   Commit and push the child before touching the parent pointer, per the parent's rule that a pointer may only reference a commit available from the child's remote. The parent's validation block in `AGENTS.md` no longer lists graph-memory after step 8, so re-read it before running.

### C. Manual step for the user

10. **Archive the private repository** `AhmedKishki/graph-memory-ultra-rag-mcp-server` (repository settings, or `gh repo archive` where `gh` is installed; it is not installed in this sandbox). Archiving, not deleting, keeps the history and keeps the archived `legacy/ultrarag-wrapper` branch's link resolvable.

## Validation

- Child: `ruff format --check .`, `ruff check .`, `pytest` (all tests), `pytest tests/test_performance.py`, `scripts/check_sqlite_fts5.py`, `uv build` — green on 3.11 and 3.12; the oracle run recorded in the parity audit.
- Child CI: all three workflows green on the pushed branch before `main` moves.
- Documentation: the new tool-count test fails when the registered surface and the documented surface disagree; a manual re-read of the drift table shows no remaining stale number.
- Parent: `git submodule status --recursive` shows no `+` or `-` prefix for the memory server and no graph entry; `git diff --check` clean; the parent README describes the product the child actually ships.

## Risks

- **Force-pushing `main`.** Mitigated by pushing `legacy/ultrarag-wrapper` first, staging the new line as `typed-store` for CI, and pinning `--force-with-lease=main:bd7bbef`. Recovery is `git push origin bd7bbef:main`.
- **The oracle has never run on this code** and is the only evidence that eight ported tools still behave like the reference after M2's additions. If it fails, the release waits; a documented, reproducible failure is better than a silent skip.
- **The timing-sensitive performance suite** can fail on a loaded machine. Run it on a quiet machine, as its own docstring requires, and do not treat a load-induced failure as a regression.
- **No test checks the documents against the code**, which is how six stale claims survived. Step 3 adds the first such check; a documentation test would close the rest of that class of defect.
- **Linux x86-64, SQLite FTS5, and `uv` 0.12 are hard prerequisites.** An install elsewhere fails at the FTS5 probe by design.
- **Neither line is tagged**, so there is no release artifact to point at. The version in `pyproject.toml` and the collection's pinned commit are the release record, consistent with every sibling.

## Out of scope

Multi-hop relation path search, session/durable tiers, operative rules, approval states, modifiers, counters, `memory.jsonl` export/import, the deterministic Markdown view, the `verify` command, dense or semantic retrieval, any browser view, and any git tag or GitHub Release.
