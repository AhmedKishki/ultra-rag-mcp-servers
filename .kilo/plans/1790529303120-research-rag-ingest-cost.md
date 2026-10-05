---
name: 1790529303120-research-rag-ingest-cost.md
description: Preserve generation-manifest evidence for the header-dependent vector-reuse defect.
---

# Header-dependent vector reuse: retained measurements

## Measurement context

- Project measured: `/mnt/DATA/projects/ai-and-fetishism`.
- Adding three PDFs rebuilt 19,595 chunks, of which 195 were new.
  - The operation took about 30–40 minutes.
- The recorded diagnosis concerned `chunking.headers = true` at `.research-rag/config.toml:13`.
  - The implementation looked up vectors by canonical `contents`, then rejected reuse when the embedded `title + contents` differed.
  - Original code reference: `src/research_ultra_rag_mcp/ingestion.py:1612-1628`.
- These are retained observations, not instructions for the current app or permission to change the measured project.

## Generation-manifest observations

| Build | docs reused | chunks reused | vectors reused | embedding |
|---|---|---|---|---|
| 20260925T135126Z, headers off | 62 | 14,294 | 14,294 | 18.6 s |
| 20260927T153510Z, headers on, +3 sources | 81 | 19,400 | 0 | 1,745 s |

- The original comparison cited `MEASUREMENTS.md:515-530`: headers and no headers produced identical results across 30 judged queries.
  - That citation records the comparison's provenance; it is not a locator in the current document.
- Comparable pre-header builds measured 15.2 s and 18.6 s of embedding.
- The recorded full-rebuild baseline contained 84 documents.

| Generation | extraction | chunking | embedding |
|---|---|---|---|
| 20260926T020452Z | 459 s | 75 s | 1,096 s |
| 20260927T153510Z | 10.9 s | 10.6 s | 1,745 s |

## Original estimates and acceptance criteria

- Estimated full-rebuild wall time: 1,600–2,400 s, against a 1,800 s per-call work budget.
  - A 3,000 s work budget was proposed to avoid a second call, not to make embedding faster.
- A header-policy change invalidated reuse through `load_reuse_snapshot`.
  - Original code reference: `src/research_ultra_rag_mcp/generation.py:108-140`.
- The proposed regression check required all unchanged documents, chunks, and vectors to be reused after a source addition, with 15–20 s of embedding.
  - The before/after retrieval evaluation had to agree or report the difference.
  - These estimates and criteria are not measured outcomes.
- Current implementation rules and validation commands belong to `research-rag/AGENTS.md` and `research-rag/MEASUREMENTS.md`.
