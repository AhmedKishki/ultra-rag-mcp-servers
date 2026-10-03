---
name: 1790946612441-research-rag-retrieval-quality.md
description: Define isolated fixed-model retrieval experiments, valid measurements, and the evidence required before changing retrieval policy.
---

# Fixed-model retrieval: evidence units, relevance, and redundancy

## Scope

- Keep the current BGE-small embedding model and MiniLM reranker, their revisions, and their weights.
- All inference stays local; no larger model, added neural model, hosted API, fine-tuning, or model download is in scope.
- Repair the experiment harness and evaluation machinery, and reevaluate the experimental sequence.
- Test candidate policies in disposable project/code copies.
- Do not change shipped retrieval defaults or activate a live generation without a separate reviewed choice.
- Suppress copied text and overlapping evidence at search time, never during ingestion.
- Preserve independent arguments and contradictory claims.
  - Aggressive cross-source semantic collapsing is outside the selected design.

- Preserve the research contract in `research-rag/AGENTS.md`: project-local generations, original-file quote authority, reviewed overlays, and one service shared by all surfaces.
- Do not patch UltraRAG, depend on a sibling project, delete sources, or introduce answer generation.
- Keep CPU/offline operation and bounded inference.
  - Report the extra work each algorithm requires.

## Evidence establishing the baseline

- Selected project: `/home/ahmed/Documents/projects/ai-and-fetishism`.
- Selected generation: `20261002T080853Z-f1ec4db7`; 102 documents, 16,254 extraction units, 24,483 chunks.
- Under 32 embedding tokens: 4,227 chunks; under 16: 2,663, of which 2,235 come from EPUBs.
- Word-normalized equality groups: 177, holding 517 redundant copies beyond their first occurrences.
- Chunker: UltraRAG/Chonkie token backend, GPT-2 384-token windows with 64-token overlap; chunks never span extraction units.
- Dense: BGE-small-en-v1.5, 384 dimensions, cached CPU ONNX, exact cosine scan of the portable float32 matrix.
- Ranking: BM25 plus dense, weighted RRF, MiniLM cross-encoder, word/cosine repetition collapse, then source-diverse selection.
- Normal `top_k=10` requests 40 candidates per retrieval half and reranks 20, with an overall rerank cap of 50.
- Search-time cosine collapse already exists at 0.99; it is not general semantic diversity selection.
- Length floors and contextual embedding headers ship off; the corpus records ten embedding-truncated chunks.
- Offline dense probes retrieve relevant sources for paraphrases but also rank an Atlas of AI index entry first for a conceptual supply-chain question.
- Direct cached-model inference reproduces a stored canonical passage vector at cosine 1.0; probes are diagnostics, not a new judged end-to-end benchmark.
- The shipped evaluation contains 32 known-item queries over 19 target passages, with one designated relevant chunk per query.
- Explicit exclusion of an unavailable source leaves 30 queries over 18 targets; record the excluded target and its reason with every derived input.
- Target-family partitions of this inspected set are exploratory, not untouched confirmation sets.
- Pooled relevance, passage usability, counterevidence, and no-answer judgments are absent.
- The artifact/model audit starts no app and runs no ingestion or official benchmark.

- Implementation owners under `research-rag/src/research_rag/`: `retrieval/search.py`, `retrieval/dense.py`, `retrieval/ultrarag.py`, `project/support.py`, `corpus/extraction.py`, and `core/tool_views.py`.
- Measurement contract: `research-rag/evaluation/README.md` and `research-rag/scripts/evaluate_retrieval.py`.
- Experiment isolation and retained run records: the standalone `research-rag-experiments` repository.

## Score interpretation

- BGE cosine is not a probability; its model card describes compressed similarity scores and recommends task-specific threshold validation.
- The current dense gate rejects below 0.72 before fusion/reranking; its 0.10 relative rescue runs only if the best eligible hit first clears 0.72.
- A best hit at 0.719 admits no dense evidence; a best hit at 0.721 admits a band down to 0.621.
- These are code-derived examples, not observed failures or evidence that either query has a relevant answer.
- RRF already uses rank rather than raw cosine; increasing or rescaling the printed scores alone cannot improve that ranking.
- Diagnose separation between judged positives and hard negatives, gate losses, and repeated generic leaders before changing the similarity metric.

## Ordered experimental work

### Prerequisites for interpreting a run

- A successful experiment preserves source bytes and records the observed algorithm, not only requested settings.
  - Finalize source/engine guards and a failed or incomplete record after exceptions and interrupts.
  - Retain each run's judged inputs, settings, patch, logs, reports, and content hashes under unique paths.
  - Test dry-run followed by real run, repeated runs, malformed reports, and report replacement.
  - Report unsupported or incomplete guards as unknown, not unchanged.
  - Copies and guards provide cooperative isolation, not an operating-system security boundary against arbitrary code.
- Candidate and rerank budgets require an observed-path check.
  - Pin candidate minimum and maximum to 40/80/160 to request those branch depths at `top_k=10`.
  - Set the rerank multiple/floor high enough for caps 20/30/50 to bind.
  - Record actual candidate depths, pool sizes, scored windows, applied reranking, and fallback.
  - Attribute pool shortfalls and budget exhaustion separately; a cap is not a measured window.
- Diagnostics do not replace judgments.
  - Ordered normalized-text equality preserves Unicode, order, multiplicity, numbers, operators, and signs.
  - Missing text is missing coverage, not an empty duplicate passage.
  - Lexical containment is an overlap diagnostic, not a semantic redundancy or contradiction label.
  - Separate repeated results within a question family from repetition across distinct families.
  - Measure candidates before and after repetition collapse; final-list duplication cannot establish rerank-budget waste or false suppression.
- Current known-item runs establish passage findability on this benchmark only.
  - Report paired outcomes by target family and treat multiple queries about one target as correlated.
  - Do not select defaults from one-query changes or repeatedly inspected exploratory partitions.
  - Keep a future authored confirmation set unused during policy development.
  - Repeated latency runs require model warm-up, balanced execution order, and explicit cold/warm labels.

### Decision sequence

- Mechanical checks can run without new labels.
  - Repeat the pinned baseline and compare ranking, stage, gate, and collapse fields while excluding explicitly named timing/path fields.
  - Publish requested-to-observed budget mappings before interpreting any grid.
  - Count designated-target losses at each stage with evaluated and unknown denominators.
  - Inspect scored candidates removed by post-rerank collapse and retain discarded provenance.
- Human evaluation gates policy acceptance, not diagnostic experimentation.
  - Freeze a rubric separating relevance, usability, and evidence relation.
  - Include verbatim copies, independent corroboration, contradictions, fragments, and author-confirmed no-answer questions.
  - Blind arm names, ranks, and model scores when presenting annotation items.
  - Keep per-query pool limits, truncation, input hashes, and adjudication reasons.
  - A union pool provides pool-relative coverage, not exhaustive corpus recall.
  - Re-present a declared subset to check annotation consistency; a repeated pass is not an independent annotator.
  - Use the toolkit's `annotation build` workflow to prepare an arm-blinded private reviewer packet from verified retained evidence.
  - Preserve candidate unions, missed designated passages, and selected collapse-pair endpoints without assigning grades.
  - Keep arm/rank/score mappings and consistency aliases in `private/`; the offline `reviewer/` page contains questions, passages, source context, and original copies only.
  - The author acknowledges the frozen proposed rubric and supplies relevance, usability, source-check, and relation judgments.
  - Keep pending grades null and uncertain grades marked for adjudication; neither becomes a negative label.
  - Save returned judgments outside the frozen packet and verify them with `annotation check --require-complete`.
  - A completed annotation is not a quality result. Implement pooled scoring as a separate app-owned protocol without changing known-item definitions.
  - Export only completed, acknowledged, adjudicated judgments using `annotation export`; unresolved labels and repeat disagreements block export.
  - Score saved labels and retained rankings through the app's `scripts/evaluate_pooled.py`, directly or through `annotation score`; run no retrieval model during this scoring pass.
  - Report graded nDCG, usable direct precision, and judged-pool coverage with denominators; never call pool-relative coverage exhaustive recall.
  - Count only annotated returned-pair relations and disclose unjudged pairs; do not infer transitive evidence groups or absence of contradictions.
  - Compare each trial separately against the baseline over the same evaluable queries within each frozen family.
  - Conditional family-bootstrap intervals are exploratory, not acceptance, superiority, or equivalence tests; insufficient families or resamples leave intervals unknown.
- Predeclare the primary endpoint, practical improvement threshold, allowable regressions, and candidate selection rule before confirmation.
  - Treat a large parameter sweep as hypothesis generation, not a collection of independent wins.
  - Use paired inference at the connected question-family level; do not count related queries or result slots as independent samples.
  - Choose confirmation-set size from the desired effect and uncertainty, not an arbitrary query-count guarantee.
- Re-chunking requires stable source-span or section-level targets plus fresh usability judgments.
  - Do not compare frozen chunk-ID scores across incompatible generations as though the target stayed fixed.
- Latency decisions require a separate repeat protocol.
  - Record cache state and background load; do not stop an existing app without authorization.
  - Interleave candidate and baseline repetitions in balanced order.
  - Separate cold startup from warm search and report sampling uncertainty rather than treating one small-sample p95 as stable.

### Evaluation and candidate policies

- Use `research-rag/MEASUREMENTS.md` for the retained exploratory observations and their limits.
- Prioritize the next comparisons by the stage evidence.
  - Build a blinded author-graded pool for the baseline and selected retrieval-depth/rerank-window alternatives, holding one work limit fixed at a time.
  - Include questions whose relevant evidence has weak lexical overlap and author-confirmed no-answer questions before comparing cosine admission with top-N admission.
  - Audit retained collapse pairs for copy identity, independent corroboration, and contradictory claims before moving collapse ahead of reranking.
  - Treat pre-rerank grouping as a conditional optimization; measure how many scores it can save at the intended work budget.
  - Compare source-only selection with novelty selection using adjudicated evidence relations, not source count or cross-query repetition alone.
  - Schedule extraction and chunk-boundary trials only after stable span targets and boundary/usability grades exist.
  - Preserve current defaults until the confirmation protocol passes.

1. **Make the measurement distinguish relevance, usability, and redundancy.**
   - Extend `scripts/evaluate_retrieval.py` with judged relevance, usability, and evidence-relation metrics.
     - Existing lexical repetition diagnostics in `research-rag/evaluation/README.md` do not supply those judgments.
     - Preserve the known-item protocol.
   - Record effective settings, engine revision, generation, chunking/model fingerprints, candidate windows, gate rejections, collapsed alternatives, and final selection.
   - Keep private judgments and passage samples outside tracked source files and do not upload them to external evaluators.
   - Build a private annotation pool from baseline and candidate results plus known missed targets, identified by source-relative path, locator, and content.
   - Have the author grade relevance and usability; do not invent human judgments from cosine, overlap, or result rank.
   - Label copied/reprinted evidence separately from related arguments, contradictions, and independent corroboration.
   - Add unusable fragments, full bibliography entries, headings, captions, short legitimate prose, no-answer questions, and user-authored paraphrases.
   - Split new development and untouched confirmation queries by target/question family; quote/paraphrase pairs stay together.
   - Label partitions of the current inspected benchmark exploratory and declare only each partition's queried targets.
   - Preserve ambiguity refusal; unresolved or excluded targets require explicit adjudication, not silent skips.
   - Report candidate recall before/after gates, usable-passage precision, unique-evidence coverage, redundancy, false suppression, boundary integrity, and p50/p95 latency.
   - Plot cosine and rerank-score distributions for positives, hard negatives, and no-answer queries; do not infer confidence from per-query min-max scores.
   - Keep this work open until relevance, usability, counterevidence, and no-answer judgments support the acceptance tests.
     - One designated chunk cannot fairly score re-chunking, equivalent passages, or deduplication.

2. **Prototype query-time quality and redundancy selection on unchanged artifacts.**
   - Work in `retrieval/search.py`, `project/support.py`, and the corresponding retrieval/core tests.
   - Compare the current pre-rerank cosine gate with top-N dense admission followed by the same MiniLM reranker and a validated final relevance gate.
   - Preserve abstention using labeled no-answer queries; neither top-N nor a relative-to-best rule alone establishes relevance.
   - Compare retrieval depths 40/80/160 and rerank budgets 20/30/50; these are test settings, not new defaults.
   - Keep lexical-only and dense-only evidence represented inside the bounded rerank pool; log the branch contribution.
   - Widen after quality/exclusion/repetition losses and score new candidates within the total rerank budget; disclose ceiling and budget exhaustion separately.
   - Group high-confidence same-text copies before spending the rerank budget, retaining every source/locator as an alternative.
     - First measure how many scored candidates post-rerank collapse discards and which target/evidence alternatives it removes.
     - Final result lists already follow repetition collapse; few final duplicates do not establish low rerank waste.
   - Preserve a representative that passes the query's filters and explicit exclusions; an excluded copy must not suppress an allowed copy.
   - Compare the source-only penalty with content-based MMR: `lambda * relevance - (1-lambda) * max_redundancy_to_selected`.
   - Combine body-vector similarity with word-shingle Jaccard/containment and known span overlap; exact shingle sets suffice for the bounded candidate pool.
   - Sweep MMR relevance weights 0.75/0.85/0.95 against the unchanged selection baseline; keep strict duplicate grouping separate from soft novelty.
   - Prefer complete, relevant evidence as a group's representative; equality normalization must preserve meaningful operators and signs.
   - Do not cluster by transitive cosine chains or lower one global hard threshold to merge every related argument.
   - Require a relevance safeguard; novelty cannot promote unrelated material just to fill `top_k`.
   - Keep original chunks retrievable through passage/context operations and bounded alternate-location disclosure.
   - Surface suppression counts, quality-driven shortfalls, and missing-vector degradation in the lean MCP response as well as the full response.
   - Keep unscored fused-tail candidates out of the scored selection unless they are reranked; retain the existing disclosed fallback if MiniLM cannot load.
   - Separate artifact-affecting identity from query-only policy before offering live gate/depth changes; preserve legacy manifest validation and log the effective query policy.
   - Reason: these changes can be measured without changing the live corpus or losing quotation provenance.

3. **Repair evidence boundaries in isolated generation experiments.**
   - Work in `corpus/extraction.py`, `corpus/text_normalization.py`, `retrieval/ultrarag.py`, `project/support.py`, and generation records/reuse checks.
   - Compare the pinned UltraRAG sentence and recursive backends with the existing token backend; the pinned remote `servers/corpus/src/corpus.py` supports all three.
   - Combine adjacent short body paragraphs within a section rather than making each EPUB element an isolated retrieval unit.
   - Preserve complete bibliographic entries and attach headings/list markers to the material they introduce; keep back matter accessible.
   - Add document/section role, constituent source spans, and boundary indicators to derived records; retain canonical text separately from index context.
   - Repair cross-page/region continuations only with explicit multi-span locators; never attribute a stitched passage to one page.
   - Distinguish decorative PDF drawings from figure/table regions and preserve reading order inside those regions.
   - Do not blanket-filter `figure`: the selected corpus contains substantive executive-summary prose under that label.
   - Count the embedding tokenizer's actual input, including context and special tokens; a GPT-2 chunk-size limit is not an embedding-token guarantee.
   - Compare body-only embedding with deterministic title/section context using the same BGE; keep canonical body text and context provenance separate.
   - Compare bounded parent/sentence-window rerank input with the current isolated chunk; respect MiniLM's joint query/context token limit.
   - Retrieve a small anchor and return its bounded reading context; merge overlapping displayed windows without counting them twice.
   - Version backend, boundaries, and extraction policy in generation identity/reuse checks, including interrupted-build identity.
   - Reason: changing chunk size alone cannot repair already-short extraction units or recover a sentence boundary.

4. **Add bounded, non-generative semantic recall experiments.**
   - Test BGE's recommended query instruction, `Represent this sentence for searching relevant passages:`, against raw-query encoding; apply it to queries only and version the effective query policy.
   - Extend `DenseBackend` with shared query encoding and `search_vector`; implement the vector entry point for exact and Qdrant backends with identical filtering and dimension/finite/nonzero validation.
   - Keep the original query ranking when lexical PRF runs; fuse the feedback ranking at a bounded weight rather than replacing the original ranking.
   - Add one Rocchio dense-feedback pass: `q_prime = normalize(alpha*q + beta*weighted_mean(feedback_body_vectors))`.
   - Test `alpha=1` with `beta=0.1/0.2`, using 1-3 distinct, complete, reranker-supported feedback passages; skip weak feedback and retain the original ranking.
   - Use representation-matched stored feedback vectors; if canonical-body vectors are absent, encode those 1-3 bodies with the same BGE and record that extra cost.
   - Feedback and refill share the query's total rerank budget; reuse per-query scores rather than rescoring unchanged query/passage pairs.
   - Rerank all feedback candidates against the original query; never treat retrieved vocabulary as a change in the research question.
   - Compare approved spelling/terminology aliases with no expansion; related concepts are not interchangeable synonyms.
   - Fit any Platt/isotonic score calibration on development judgments only; calibration serves final admission/display, not a claim of better ranking.
   - Diagnose hubness with representative queries; centering, whitening, local scaling, or query-bank correction are lower-priority ablations only if hubs remain after quality repair.
   - Geometry transforms require versioned project-local derived state, the same transform for queries/documents, and fresh gate calibration; never overwrite canonical vectors.
   - Reason: vector feedback and deterministic context can improve vocabulary reach without changing or adding a neural model.

## Validation and rollout

- Read the child `AGENTS.md` and preserve pre-existing working-tree changes; implementation edits belong inside `research-rag`.
- Baseline and query-time trials must leave the selected generation, review files, originals, and `current.json` byte-identical.
- Artifact-changing trials use a disposable initialized evaluation project with authorized source copies and matching source-relative paths, not the live project.
- Test all-identical candidates, overlap, contradiction/negation, differing numbers/operators, independent authors, missing vectors, excluded representatives, bounded refill, and short legitimate evidence.
- Test the 0.72 gate discontinuity, irrelevant queries with a strong relative leader, score calibration leakage, PRF topic drift, duplicate feedback leaders, zero/invalid vectors, and exact/Qdrant filter parity.
- Test PDF page continuations, multi-column boxes, EPUB nested anchors, abbreviation-heavy sentences, long-sentence fallback, complete references, truncation, and exact locator mapping.
- Keep tests for explicit exclusions, reviewed metadata, offline restart, atomic generation activation, and real gateway hybrid retrieval.
- Run the child validation commands and the official offline harness, with `--validate-only` first, on an approved test project; log every target-resolution failure.
- Compare policy ablations at matched observed candidate/rerank budgets; label deliberate budget sweeps separately.
- Record target presence at dense eligibility/admission, fusion, reranking, repetition collapse, and final selection.
- Mark absence from a truncated diagnostic list unknown rather than treating it as a rejection.
- Preserve ranking-metric definitions across report versions and refuse deltas across incompatible metric definitions.
- Retain source coverage and adjudicated counterevidence alongside relevance metrics.
- Accept a policy only if untouched confirmation judgments establish usable-evidence improvement without hiding distinct claims or worsening no-answer behavior.
- Report paired uncertainty by target family and repeated latency; higher cosine, more sources, and less repetition alone are not success criteria.
- Do not activate a new live generation or change shipped defaults without a separate reviewed choice; retain the old generation for rollback and report unmatched passage exclusions.
- Additional annotators, a second corpus, production thresholds, aggressive cross-source collapse, new neural models, and live activation are outside this implementation commitment.

## Research and upstream resources

- [BGE model-card FAQ](https://huggingface.co/BAAI/bge-small-en-v1.5): similarity interpretation and query instruction, not universal thresholds.
- [Pinned UltraRAG corpus](https://github.com/OpenBMB/UltraRAG/blob/3a709a2aea3fbe46acca59c422621c94b6e86857/servers/corpus/src/corpus.py) and [retriever](https://github.com/OpenBMB/UltraRAG/blob/3a709a2aea3fbe46acca59c422621c94b6e86857/servers/retriever/src/retriever.py): sentence/recursive backends and the `query_instruction`/batch-query pattern; preserve the app's identifiers and scores rather than replacing its dense backend with anonymous strings.
- [UltraRAG evaluation](https://ultrarag.openbmb.cn/pages/en/rag_servers/evaluation): TREC qrels/runs and paired permutation testing; answer-generation metrics are outside the app's contract.
- [MMR, 1998](https://doi.org/10.1145/290941.291025) and [vector PRF, TOIS 2023](https://arxiv.org/abs/2108.11044): redundancy-aware selection and efficient fixed-encoder query feedback.
- [Contextual Retrieval, 2024](https://www.anthropic.com/news/contextual-retrieval) and [semantic-chunking evaluation, 2025](https://aclanthology.org/2025.findings-naacl.114/): borrow deterministic context separation and test cheap structural segmentation; do not add a context-generating model.
- [FreeChunker, 2026](https://aclanthology.org/2026.findings-acl.730/): borrow the cross-granularity sentence-window idea, not its differently trained encoder.
- [Hubness reduction, 2024](https://proceedings.mlr.press/v233/nielsen24a.html): motivates diagnosis and optional vector postprocessing, not evidence that BGE on this corpus needs whitening.
- SPLADE, ColBERT, HyDE, LLM-generated context, MinerU's additional models, and long-context late chunking are not drop-in improvements under the fixed-model constraint.
