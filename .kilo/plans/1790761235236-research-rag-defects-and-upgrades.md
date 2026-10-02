# Cheapest upgrades: lint configuration, CI matrix, contract-derivation tests

## Context

This implements items 1 and 2 from the "On upgrades" section of the review at
`research-ultra-rag-mcp-server` `34d804a` (v0.50.0). The other findings from that review
are **not** in this change; they stay in the review plan at
`.kilo/plans/1790761235236-research-rag-defects-and-upgrades.md`.

Nothing here changes retrieval, generation contents, the answer shape, or any on-disk
layout, so no re-ingest and no measurement re-run is required.

Starting state, verified by running the tools:

- `uv run pytest -q` is green: 378 passed in ~57s.
- There is **no `[tool.ruff]` section and no `ruff.toml`**, so `ruff check` runs its default
  set only.
- Violation counts for the rules proposed below, from
  `ruff check --isolated --select <RULE> .`:

  | Rule | Violations | Where |
  |---|---|---|
  | `C901` | 24 | 22 in `src/`+`scripts/`, 2 above a threshold of 25 |
  | `BLE001` | 0 | the 3 existing `noqa: BLE001` already cover every case |
  | `ASYNC` | 8 | all `ASYNC240`; 7 in `tests/`, 1 in `scripts/`, **0 in `src/`** |
  | `SIM` | 4 | 2 auto-fixable, 2 needing judgement |
  | `RUF100` | 8 | all stale `noqa`; all 8 resolve once the rules are selected |
  | `S` | 1742 | 1709 are `S101` (assert) — **not adoptable in this change** |

- `uv.lock` already pins **373 `cp311` wheel references** and declares
  `requires-python = ">=3.11, <3.13"`, so 3.11 resolves from the existing lockfile. No
  `uv lock` change and no new resolution is needed.
- No 3.12-only API appears anywhere in `src/`, `tests/` or `scripts/`: no PEP 695 generics,
  no `itertools.batched`, no `Path.walk`, no `typing.override`, no `StrEnum`. The only
  version-sensitive import is `from datetime import UTC` (`health.py:30`, `support.py:17`),
  which is 3.11+. So the 3.11 matrix should be green without code changes.

## Commit 1 — a ruff configuration that matches the stated contract

Add to `research-ultra-rag-mcp-server/pyproject.toml`:

```toml
[tool.ruff]
# The default set (E4, E7, E9, F) stays selected; these are added on top of it.

[tool.ruff.lint]
extend-select = ["ASYNC", "BLE001", "C901", "RUF100", "SIM"]

[tool.ruff.lint.mccabe]
# Permits the 22 functions already between 11 and 23, and fails anything new
# above 25. The two that exceed it carry a targeted noqa naming the tracked
# work, so this stays green while a third function cannot slip through.
max-complexity = 25

[tool.ruff.lint.per-file-ignores]
# Tests and benchmark harnesses are async coroutines that touch the filesystem
# by design and serve no concurrent traffic. src/ keeps the rule.
"tests/**" = ["ASYNC240"]
"scripts/**" = ["ASYNC240"]
```

Then land the config so the suite is green:

1. **The two `C901` exceptions**, as inline noqas, not global ignores — a global ignore
   would hide new violations everywhere, which defeats the point.
   - `src/research_ultra_rag_mcp/ingestion.py:795` `_advance_ingestion` (107). Noqa with a
     comment naming `TODO.md:45`, the tracked split. Remove the noqa when that lands.
   - `src/research_ultra_rag_mcp/search.py:544` `search` (42). Noqa with a comment stating
     the number and that the threshold is not a refactor schedule. This function is **not**
     currently in `TODO.md`; if the comment needs a tracked item, add one there rather than
     letting the noqa be the only record.
2. **`RUF100` — do not "fix" these.** All 8 flagged `noqa` resolve once the rules are
   selected: the 3 `noqa: BLE001` (`settings.py:243`, `doctor.py:335`, `health.py:271`) and
   `health.py:298` become used because `BLE001` is now enabled, and the 4 `noqa: F401`
   re-exports at `service.py:30`, `:36`, `:40`, `:56` stay used because `F` is in the
   default set. Verify with `ruff check` before touching any of them — deleting them would
   be the wrong fix.
3. **`SIM` — 2 auto-fixable, 2 by hand.**
   - Auto: `SIM300` Yoda conditions at `tests/test_rerankers.py:22` and
     `tests/test_service.py:4109`. Fix with `ruff check --fix`.
   - `SIM108` at `src/research_ultra_rag_mcp/search.py:122` wants
     `unit = None if vector is None else normalised(vector)`. Apply it, but note this is the
     same block as review finding D (the `kept`/`kept_vectors` index desynchronisation at
     `search.py:126-144`), which is **not** fixed here. Keep the two edits separable so the
     finding-D fix later has a clean diff.
   - `SIM105` at `src/research_ultra_rag_mcp/config.py:333` wants `contextlib.suppress`.
     Apply only if it does not lose the comment explaining why the `OSError` is swallowed;
     otherwise leave it and record why.
4. **`ASYNC240` — 0 in `src/`,** so the per-file-ignores leave the source tree clean. Do not
   fix the 7 test sites or the 1 script site; the ignores are the intended outcome.
5. **`BLE001` — no change needed.** 0 violations today because every blind `except`
   re-raises. Enabling the rule is what stops a future one from swallowing a fault.

Deliberately **not** in this change: the `S` (bandit) family. At 1742 violations, 1709 of
which are `S101` on legitimate test asserts, adopting it wholesale is not a "cheap" change.
The 33 non-`S101` findings (`S603` ×17 subprocess, `S608` ×6, `S105` ×4, `S108` ×5,
`S607` ×1) each need individual judgement and belong in their own pass.

## Commit 2 — CI that tests what the package declares, with a timeout

`.github/workflows/test.yml` currently runs one Python version, 3.12, while
`pyproject.toml` declares `>=3.11,<3.13`. **3.11 is supported and never tested**, and
nothing in the dependency tree needs the `<3.13` cap.

1. **Add a matrix on 3.11 and 3.12**, with `fail-fast: false` so one version's failure does
   not hide the other's.
2. **Pass `--python` to `uv sync` explicitly.** This is the one detail that will otherwise
   silently no-op: the repo contains `.python-version` containing `3.12`, and uv gives that
   file precedence over the interpreter `actions/setup-python` provides. Without an explicit
   flag the matrix would run 3.12 twice and look green. Use
   `uv sync --frozen --python ${{ matrix.python-version }}`.
3. **Add `pytest-timeout` to the `dev` dependency group** and a bound in
   `[tool.pytest.ini_options]`, e.g. `--timeout=300 --timeout-method=thread`. There is no
   timeout today, and several tests spawn real subprocesses (the integration test is already
   17s), so a hang blocks CI indefinitely with no diagnostic. Use
   `--timeout-method=thread`, not the `signal` default: `signal` misses a hang inside a C
   extension such as ONNX inference, which is exactly the failure this guards against. Note
   in the commit message that `thread` kills the whole pytest process after dumping every
   thread's stack — that is the wanted behaviour for CI, and it is why the method is not the
   default.
4. **Add `uv run python -m compileall -q src tests`** to the workflow. It is already in the
   validation list at `AGENTS.md:314-320` but missing from CI.
5. **Do not widen `requires-python` in this commit.** Leave `>=3.11,<3.13` until the matrix
   has actually run green on both versions. Widening the range is a separate decision that
   should follow evidence, per `AGENTS.md:53` (never implement a choice that changes
   on-disk or artifact behaviour before the user has chosen it — the same principle applies
   to a declared support range).

## Commit 3 — derive the contract from the code, and correct three wrong claims

Three lines of `AGENTS.md` are factually wrong. Nothing catches them because
`tests/test_documentation.py` asserts **strings** rather than deriving values, which is the
recurring defect class in this repo. Fix the claims and add the guards in one commit, so
the commit is self-verifying.

### The three corrections

- `AGENTS.md:14`, `:112`, `:155` say "nine public tools". `server.py` has **7**
  `@app.tool` (`:322, 373, 404, 455, 475, 496, 527`) and 2 `@app.resource`
  (`:344, :356`). Write "seven public tools" at `:14` and `:155`. At `:112`, **drop the
  number** rather than replacing it: the sentence constrains browser *write* endpoints, and
  the two resources are read-only projections, so the write surface is not the tool count
  under any reading. The test below asserts a count only where a count is stated.
- `AGENTS.md:66` pins the shared UI at `f001f90`; `pyproject.toml:28` and `uv.lock` pin
  `4f3f7b6`. Correct it to the pin that is actually used. Do **not** bump the dependency to
  the checked-out `881f6a4` here — that commit changes control hiding and argument
  forwarding, which `AGENTS.md:101` and `ResearchUIAdapter.call` govern, and it needs the
  UI package's own tests green first per `AGENTS.md:324`.
- `AGENTS.md:101` says the UI profile turns off `metadata=False, metadata_filters=False`.
  `ui.py:76-87` sets both `True`, which is correct — `set_source_metadata` is a public tool
  and `search` accepts the filter layers. The true disabled set is exactly
  `retrieval_modes`, `reranking`, `chunk_settings`. **The contract line is the wrong one**,
  so correct the doc, not the code, and say so in the commit message.

### The three tests

Add to `tests/test_documentation.py`, which is already the home for prose-versus-code
checks.

- **Tool count.** Parse `src/research_ultra_rag_mcp/server.py` with `ast` and count
  `FunctionDef` nodes carrying an `app.tool` / `app.resource` decorator. Assert the count
  equals the number stated in the two `AGENTS.md` phrases. Use `ast` rather than importing
  the module: it counts declarations, has no import side effects, and cannot be satisfied by
  a runtime object that disagrees with the source.
- **Pinned commits.** Parse `pyproject.toml` with `tomllib` (3.11+, already used by the
  pinned config library) and extract the commit SHAs from the dependency URLs. Read the
  baseline lines out of `AGENTS.md` and assert each pin matches, plus that the stated
  `version` matches `pyproject.toml`'s. This covers the `f001f90` drift and any future one.
- **UI capabilities.** Import `RESEARCH_UI_PROFILE` from `research_ultra_rag_mcp.ui` and
  assert the disabled set it names is the set `AGENTS.md:101` names. `test_ui.py` already
  imports this module, so the dependency is present.

These fail when a tool is added or a pin moves, which is the intent: `AGENTS.md:22-30`
requires the document to describe the present, and a guard that fails on drift is what makes
that hold over time rather than by discipline.

## Validation

Per `AGENTS.md:314-320`, after each commit:

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
uv run python -m compileall -q src tests
```

Commit-specific:

- **Commit 1**: `uv run ruff check .` must be clean, not merely non-increasing. Then confirm
  the config is actually doing something by proving it bites: temporarily add a function of
  complexity 26 and confirm `C901` fires, and temporarily add
  `except Exception: pass` and confirm `BLE001` fires. Revert both probes.
- **Commit 2**: the matrix must show **two distinct Python versions in the job log**, not
  one twice. If both jobs report the same version, the `--python` flag did not take effect
  and the change is inert. Confirm a real hang is caught by temporarily inserting
  `time.sleep(600)` into a test and checking the job fails with a thread dump rather than
  running until the GitHub limit.
- **Commit 3**: `tests/test_documentation.py::test_markdown_has_no_hard_wrapped_prose` must
  still pass. That test requires every paragraph to be a single unwrapped line, so **each
  edited `AGENTS.md` line must stay one line** — this is the most likely way to break the
  suite with this commit. Then prove each new test bites by inverting one expectation and
  confirming the failure, and by adding a throwaway 8th tool to `server.py` and confirming
  the count test fails.

After the third commit, push the child repository, then the parent pointer, per
`AGENTS.md:290` and the parent `AGENTS.md` "Work on one server".

## Risks

- **The lint commit touches 4 unrelated test lines** via `--fix` on `SIM300`. Keep that
  mechanical, clearly separate hunk out of any other change so a reviewer can skip it.
- **`max-complexity = 25` is a judgement, not a derivation.** It is chosen so the existing
  22 functions pass and only the two already-tracked ones need a comment. If the implementer
  prefers a lower bar, the commit grows by 22 refactors and stops being cheap — in that case
  raise the threshold rather than refactoring, and record the choice.
- **The CI matrix costs roughly double the CI minutes**, and the integration test is 17s of
  that. Acceptable, but if it becomes a problem the fix is to run the full suite on 3.12 and
  a fast subset on 3.11, not to drop 3.11.
- **`--timeout-method=thread` kills the pytest process on a hang** rather than failing one
  test. That is correct for CI and wrong for a developer's long local run; if that becomes
  annoying, keep the flag in the workflow rather than in `addopts`.
- **Correcting `AGENTS.md:101` is a contract change.** It removes a stated requirement that
  the code never met. That is the right direction, but it is a decision about the contract,
  so flag it in the commit message rather than burying it in a lint commit.

## Open questions

None blocking. One thing to raise with the user rather than decide silently: whether to
widen `requires-python` to include 3.13 once the 3.11/3.12 matrix is green. That is a
support-policy decision, and this plan deliberately stops before it.
