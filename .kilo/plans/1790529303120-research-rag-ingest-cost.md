# Cut research-rag ingest cost on ai-and-fetishism

## Context

Adding sources to `/mnt/DATA/projects/ai-and-fetishism` costs about 30-40 minutes. Adding three PDFs rebuilt 19,595 chunks when only 195 were new.

Cause: `/mnt/DATA/projects/ai-and-fetishism/.research-rag/config.toml:13` sets `chunking.headers = true`. The embedding phase reuses a vector by looking up the hash of the canonical `contents`, and refuses to reuse when the text it will embed differs (`src/research_ultra_rag_mcp/ingestion.py:1612-1628`). With a header, the embedded text is `title + contents`, so no key ever matches and every chunk is embedded.

Measured on this project's generation manifests:

| Build | docs reused | chunks reused | vectors reused | embedding |
|---|---|---|---|---|
| 20260925T135126Z, headers off | 62 | 14,294 | 14,294 | 18.6 s |
| 20260927T153510Z, headers on, +3 sources | 81 | 19,400 | 0 | 1,745 s |

`MEASUREMENTS.md:515-530` records headers measured identical to no headers on this corpus across 30 judged queries, and the packaged default is off for that reason.

## Change

One line in the project config. No code, no artifact format change, no server repository change.

```
# /mnt/DATA/projects/ai-and-fetishism/.research-rag/config.toml
[chunking]
headers = false
```

The comment above the key explains the opposite choice and must be rewritten to state the measured reason for off.

## Steps

1. Stop the resident build. It is embedding a generation with headers on, so the flip in step 3 discards it. Find it by CPU time, not by a recorded pid:

   ```bash
   for p in $(grep -a -l "research-ultra-rag-mcp" /proc/*/cmdline | cut -d/ -f3); do echo -n "$p "; cut -d' ' -f14,15 /proc/$p/stat; done
   ```

   Take the pid with the large user-time figure. A clean SIGTERM loses at most one 64-chunk batch; the checkpoint is durable. Generation `20260927T153510Z` stays selected.

2. Record the before state. Read `runtime/.../current.json` and the selected manifest's `build_metrics.phase_timings_seconds`, `reused_document_count`, `reused_chunk_count`, `reused_vector_count`. Confirm the resident build left `staging/` behind; the next build discards it once the identity no longer matches.

3. Run the before evaluation, with no build running, from the server checkout:

   ```bash
   cd /mnt/DATA/ultra-rag-mcp-servers/research-ultra-rag-mcp-server
   uv run python scripts/evaluate_retrieval.py --project /mnt/DATA/projects/ai-and-fetishism --offline
   ```

4. Edit the project config as above.

5. Restart the MCP server. `ResearchService` resolves settings once at connect, so a running server keeps the old value in memory and would rebuild with headers on again.

6. Call `ingest` until it answers `ready`. Expect one or two calls, see below.

7. Record the after evaluation with the same command as step 3 and compare. `MEASUREMENTS.md:515-530` predicts every column identical; a difference is a finding to report, not a threshold to argue past.

8. Prove the fix on a real addition. Drop one PDF into `/mnt/DATA/projects/ai-and-fetishism/sources`, call `ingest`, and read the new manifest's `build_metrics`. Pass condition:

   | Counter | Expected |
   |---|---|
   | `reused_document_count` | every unchanged document |
   | `reused_chunk_count` | every unchanged chunk |
   | `reused_vector_count` | every unchanged chunk |
   | `phase_timings_seconds.embedding` | 15-20 s |

   The comparable pre-header builds on this project measured 15.2 s and 18.6 s of embedding.

## What the first rebuild costs

Flipping the setting invalidates the current generation as a reuse baseline, because `load_reuse_snapshot` compares `chunk_headers` and returns `None` for a mismatch (`src/research_ultra_rag_mcp/generation.py:108-140`). Step 6 therefore re-extracts, re-chunks, and re-embeds all 84 documents, not just the header-bearing text.

Comparable full rebuilds on this project:

| Generation | extraction | chunking | embedding |
|---|---|---|---|
| 20260926T020452Z | 459 s | 75 s | 1,096 s |
| 20260927T153510Z | 10.9 s | 10.6 s | 1,745 s |

Budget 1,600-2,400 s wall for step 6, and expect the 1,800 s default budget to return `in_progress` at least once. Only step 6 is slow; step 8 is not.

## Optional

`ingestion.work_budget_seconds = 3000` in the same config file makes step 6 finish in one call instead of two. It changes no artifact and makes nothing faster, and it stops mattering once step 8 passes. Omit it under a least-invasive rule.

## Validation

- Step 3 and step 7 evaluations agree, or the difference is reported.
- Step 8 hits the reuse counters and the embedding timing above.
- `git -C /mnt/DATA/projects/ai-and-fetishism status --short` shows the config change and no source-file edits.

## Risks

- **Flipping back on costs a full rebuild.** `chunking.headers` is an identity setting. Restoring it discards the reuse baseline and re-runs step 6. `TODO.md:29` is the durable fix that would make headers cheap again; it stays open.
- **The resident build is killed mid-phase.** At most one bounded batch is redone. If the server writes a failure record, the next build discards the staging root anyway.
- **A source added during step 1-5 joins the step 6 rebuild for free.** A source added after step 6 needs its own ingest, which step 8 prices.

## Out of scope

- `TODO.md:29`, reuse across a header change. Needed only if headers return.
- `TODO.md:15`, reads during a build. Code change in `research-ultra-rag-mcp-server`, and the window it closes is one ingest call wide after step 8.
- `TODO.md:16`, a budget argument on `ingest`. The optional line above covers the one case that exists.
- `runtime.embedding_threads`. No effect once only new chunks are embedded.
- `TODO.md:25`, generation pruning. Disk, not ingest time.
