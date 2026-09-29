# Semantic memory lookup: the base

**Goal:** make a memory lookup work without assuming the caller's wording. Recording is asynchronous and may take as long as it takes; a lookup is blocking and must stay fast. Any **local** means is in scope to achieve that, and no API may be used at this stage. Quality is measured in a later phase; this phase builds the base that a measurement can be run against, and claims nothing about quality.

## The performance model, and what it is not

There are two clocks, and they are not symmetric.

**Recording is async.** `set_memory_*` appends the statement to `MEMORY.md`, returns, and the derived work happens afterwards. This is safe because the derived state is derived: the Markdown is the record, the index is not. If a process dies before an embedding lands, the unit is still in the file, and the next sync re-discovers it as pending. Nothing is lost by being slow, because nothing slow is the record.

**A lookup is blocking.** It may do O(1) work and no more: embed the query once, scan the vectors once, query the lexical index once, fuse, return. It may not backfill, re-embed, or load a model. Anything a read would wait for belongs on the write side, which has no deadline.

**What the write side must guarantee** — three requirements, none of them a time budget:

1. Durability first. The statement is in the file before any derived work begins.
2. No work proportional to the memory's size. A write embeds the one string it just added; it never passes over the rest of the memory.
3. A write never fails because of the lookup layer. A model that cannot be fetched leaves the unit pending and says so.

**Why the research server's profile does not transfer.** Its ingestion is extract → chunk → embed a whole corpus → build a BM25 index → produce a generation, and a new generation redoes all of it; that is why new material is expensive there and a stable corpus is the cheap operating mode. None of those stages exists here. Recording is a short append; there is no corpus embedding pass and no generation. The vectors here are produced **one at a time as units are recorded**, in proportion to what was actually recorded, so the cost that dominates the research server cannot be reintroduced by adding them.

**The model stays off the blocking path.** A read that loads a model pays for it in seconds, so the server warms it on the write side — at startup, and lazily if a write is the first thing that needs it. A read that finds it cold reports that the semantic side was unavailable, which is a fact about the answer rather than a stall.

## Architecture

### Today

```
set_memory_*(content)
  └─ store.append_statement      append one block to MEMORY.md          O(1)

get_memory_*(query, limit)
  └─ read_standing                create the scope if absent            O(1) file
  └─ index.sync()                 re-read only changed files        O(files, see below)
  └─ FTS5 MATCH, ORDER BY rank    lexical ranking, LIMIT cap + 1        O(index)
  └─ units[]                      only what matched
```

One derived artefact, `index.sqlite3`: FTS5 over the parsed statements and rounds, rebuilt in seconds, safe to delete.

### After

```
set_memory_*(content)                              blocking part: the append
  └─ store.append_statement                                             O(1)
  └─ unit_key = digest(text)                  stable identity            O(1)
  └─ {"embedded": false, "pending": n}         durable, answered
  └─ background: embedder.embed([text])        ONE string, no instruction  O(1)
     └─ vectors.insert(unit_key, model, dim, vector)                     O(1)

get_memory_*(query, limit)                          blocking: O(1) model work
  └─ model resident?  no → semantic side unavailable, say so, lexical only
  └─ embedder.embed([query])                 ONE string, query instruction O(1)
  └─ dense: exact cosine over the active model's vectors                  O(units × 384)
     └─ floor 0.72, plus the 0.10 relative margin around the query's best
  └─ lexical: FTS5 MATCH, ORDER BY rank, LIMIT pool + 1                  O(index)
  └─ fuse: weighted RRF, bm25 1.25 / dense 1.0, rrf_k 60
  └─ rerank stage: off by default; if on, scores the fused candidates
  └─ units[] with per-unit matched_by and scores, capped by limit
```

New derived artefact, `index-vectors.sqlite3`, one row per unit. **Separate from `index.sqlite3` on purpose:** their economics are opposite. The lexical index is rebuilt in seconds; the vector index costs one embedding per unit and is filled at record time, so deleting it means re-embedding what was recorded. A project that commits `.memory-rag/` can ignore the pair without coupling them.

## The seams, so "any local means" is a decision and not an architecture

The store and the index never import a model library. They are written against two small protocols:

- **`Embedder`** — `embed_documents(texts) -> vectors`, `embed_query(text) -> vector`, `identity() -> model id and dimension`. A query and a unit are embedded differently, which is why they are two methods and not one.
- **`Reranker`** — `score(query, candidates) -> scores`, `identity()`.

One local implementation of each ships now. Because the seam is the interface, a stronger local model is a one-line configuration change, and a hosted backend later is additive rather than a rewrite — which is what "no API at this stage" should mean if it is to stay a stage rather than a vow.

All of it is configuration, not code: embed model, cosine floor, relative margin, fusion weights, `rrf_k`, pool depth, rerank on/off and model, and the read-latency ceiling are one frozen settings object read from one place, so the later phase can sweep them without touching call sites.

### The local candidates the later phase chooses between

All are in the collection's already-pinned library, so each is one line rather than a project. Sizes are the rough download; the deciding axis for every one of them is **blocking read latency against quality, both recorded**.

| Role | Options (local, CPU) | Note |
| --- | --- | --- |
| Embed | `BAAI/bge-small-en-v1.5` — 384-d, ~65 MB | The default, and the only one the collection has measured numbers for. |
| Embed | `jinaai/jina-embeddings-v2-base-de` — 768-d, multilingual | Stronger and much larger; already cached on this machine. A memory may not be English. |
| Embed | `sentence-transformers/all-MiniLM-L6-v2` | The smallest and fastest; the floor of the range, useful as a lower bound to measure against. |
| Rerank | `jinaai/jina-reranker-v1-tiny-en`, `Xenova/ms-marco-MiniLM-L-6-v2` | **Affordable on a blocking path.** These invalidate my earlier claim that reranking costs 2.3 s: that was `BAAI/bge-reranker-base`, 278M parameters. |
| Rerank | `BAAI/bge-reranker-base`, `jinaai/jina-reranker-v2-base-multilingual` | The measured-but-expensive end of the range; 2.3 s per query is a real cost on a blocking call. |
| Retrieval shape | single dense vector (default) vs. late interaction, token by token | Late interaction can match *words inside* a one-line unit, which suits short memories better than one vector does — at more space and more time per query. A candidate, not a recommendation. |

The floor stays whatever wins: without it a dense side always answers, and always answering is worse than declining.

## The one cost this plan does not fix, and should

`sync()` runs before every search, and it is **O(files in the scope), not O(changed files)**. It globs the rounds directory and, for every file, stats it *and opens it to read the first 4 KB* to recompute the head digest that distinguishes an append from an edit. A few hundred daily files is nothing; a few thousand puts a read into the hundreds of milliseconds. The sibling measured the same class of cost and rejected a cache that would report a changed corpus as fresh, so the sweep is deliberate there — but there it guards a build, while here it sits on a blocking read. This is in the shipped code today, not something the semantic side introduces.

Three ways out, and each trades the property that a hand edit is noticed automatically:

- **Write-path maintenance (recommended).** `set_memory_*` and the page's writers already know the fingerprint they just produced, so they record it; a read then stats and reads nothing. A hand edit is invisible until an explicit reindex, which means adding that command and stating the property change plainly in ADR 0001 rather than leaving it implied.
- **Stat-only fingerprints.** Keep `(size, mtime_ns)`, drop the 4 KB head digest. The sweep becomes stat-only instead of read-per-file, and is still O(files) — better, not good.
- **Bounded rotation.** A read verifies K files per call, round-robin, and reports how many it did not check. Latency bounded, a hand edit noticed within a bounded number of reads, and the answer says so meanwhile.

This is orthogonal to the semantic work and can ride in the same change or be deferred. If it is deferred, the read-latency ceiling in the validation section below must be asserted against a scope with a realistic number of daily files, so the ceiling is measured rather than assumed.

## Precision over coverage, because the consumer is a context window

Every unit returned is text an agent must read and a model must generate over, so the goal of a read is **the fewest units that still answer the question**:

- The returned set is exactly `limit`. The sibling's paraphrase reach rose 54.5% → 72.7% going from 10 to 50 results, and that is a cost, not a benefit, to whoever must read 50 passages.
- Fusion is the ordering lever the measurements support: hybrid beat BM25 alone on succ@1 (59.4% → 65.6%) at identical reach — ordering improves, coverage does not move.
- Dense **alone** is the weakest mode (succ@1 62.5%, fewest passages, 5.3) and its worst class is proper nouns: "a proper noun needs the words to match, which is what BM25 is for". A memory is largely proper nouns, paths, and identifiers like `MAT-100`. Both sides are therefore permanent, with the sibling's measured constants — `rrf_k = 60`, `bm25_weight = 1.25`, `dense_weight = 1.0`, floor `0.72`, margin `0.10` — adopted rather than invented.
- **Reranking is a first-class candidate, not a distant seam.** It is the largest single ordering gain measured anywhere in this collection (succ@1 65.6% → 81.2%, returning 6 passages instead of 50), a cheap local model makes it affordable, and it was measured on long passages rather than one-line units. It ships **off**, reporting that it is off, until a measurement on this data says otherwise.

## An exact scan, not an approximate index

384 float32 is 1.5 KB per unit, so 10,000 units is 15 MB; one numpy pass is milliseconds and exact. The sibling measured an ANN index at 0.5–6 s per query at 19,400 chunks because every query reopened it. At memory scale that is the wrong trade, and it would also put a per-query index open on a blocking path. `numpy>=1.26,<3` is pinned explicitly, as the sibling does.

## A stable unit key

Units are identified today by `(source, stamp)`, and a statement's stamp is a block ordinal that shifts when a hand edit inserts a block above it. A vector keyed on that would be silently wrong after an edit. The vector key is `sha256` of the unit's normalised text: stable under reordering, and a changed statement is a different key, so the old vector becomes collectable rather than wrong. The FTS5 table gains an unindexed `unit_key` column, so a sync can tell which units have no vector without a second parse.

## Compatibility: what breaks and what does not

| | Verdict |
| --- | --- |
| The record — `MEMORY.md`, `project/<date>.md` | **Untouched.** Same names, same bytes, same template. The differential against a real UltraRAG checkout is the gate. |
| A UltraRAG UI reading the global memory | **Untouched.** It reads `<storage-root>/memory/default/`. |
| Ingestion and regeneration cost | **Unaffected, by the argument above.** Recording stays an append; there is no corpus pass and no generation to rebuild. |
| The read payload | **Differs more than before.** Upstream returns the whole document; ours returns matched units, and will carry `matched_by`, fusion scores, and whether the semantic side was available. ADR 0001's recorded surface difference grows. |
| ADR 0001's "no model of any kind" and the README's "no search by meaning" | **Must be amended, or this change is refused.** Both are stated as deliberate properties and this change makes them false. |
| `NOTICE` | **Must gain** the embed model and the library, with their licences. |
| Install story | **Changes.** From "no network, no model" to one fetch on first use, into this package's own cache, never a sibling's. |
| "Delete the index and it rebuilds" | **Still true, no longer free.** `index.sqlite3` costs seconds; `index-vectors.sqlite3` costs one embedding per recorded unit. Documented per file. |

## What this phase does not do

- **No quality claim.** The ADR amendment records the semantic side as *unmeasured* and names the phase that measures it.
- No backfill on the read path, and no corpus pass anywhere.
- No reranking enabled by default; the stage exists, is off, and says so.
- No hosted model or API of any kind — a stage constraint, enforced by having the only shipped implementations be local.
- No change to the four tool names or parameters. `set_*` gains response fields.

## The seam the later phase needs, built now

- `embedded`, `units_pending`, `semantic_available`, `matched_by` per unit, and fusion scores in every read and write: the counters a harness reads.
- The model fingerprint inside the vector index, so a measurement is re-runnable against a known model.
- A rerank stage that reports `off`, and settings for every lever above, so a sweep is configuration rather than code.
- The fidelity and differential tests, keeping the record provably upstream's whatever the derived layer does.

The later phase adds `scripts/evaluate_lookup.py` and a committed judged set, and decides with numbers: which embed model, whether a cheap rerank earns its place on a blocking call, and whether the semantic side beats words at all on this data.

## Decisions taken by default, each reversible in one line

- **Default embed model** `BAAI/bge-small-en-v1.5`, because the collection has measured numbers for it and it is the smallest strong option.
- **Fusion constants** the sibling's measured ones, revisited only against our own measurement.
- **Rerank off until measured**, with a cheap local model one line away.
- **A write never fails because of the model**, and a read reports a missing model rather than stalling.
- **Vectors in a file separate from the lexical index**, because their rebuild costs differ by orders of magnitude.

## Validation for this phase

- A **read-latency ceiling** asserted with a warm model, so a later change cannot quietly make blocking reads slow. The cold-model first read is outside the bound and must be disclosed.
- **No size-proportional model work on either path**: a write after a populated store does not re-embed the store, and neither does a read. The lexical sync sweep is a separate, pre-existing cost and is addressed in the section above rather than by this line.
- **Durability before derived work**: a write whose embedding fails still leaves the statement in the file and reports `embedded: false` with a pending count.
- **The seams hold**: the store and the index import no model library; a fake embedder and a fake reranker drive the whole test suite, so no test needs a model.
- **Sync correctness**: a hand edit is read, a changed statement gets a new key, a deleted file loses its units, a changed model invalidates the vectors.
- **Fusion labelling**: a unit matching only lexically, only semantically, or both is labelled correctly, and an irrelevant query abstains rather than returning the nearest thing.
- **Isolation unchanged**: a project's memory still cannot be reached from another project's read.
- **The differential still reports identical standing bytes and identical round bytes.** If it does not, the record moved and this change is wrong.
