# RAG evaluation

Offline evaluation of retrieval and answer quality over a fixed golden dataset
([CWYD-11](https://goncalvesmarques.atlassian.net/browse/CWYD-11)). Every change to chunking,
retrieval, the evidence threshold, the reranker or the chat model can be compared with numbers.
Rules: DOM-20 and DOM-21 in [`docs/domain-context.md`](../domain-context.md).

## Run it

```bash
docker compose up --build --wait                  # stack running (the eval waits for the API's migrations)
docker compose --profile eval run --build --rm eval       # every configuration, ~1 min, under US$ 0.01 with claude-haiku-5-5
docker compose --profile eval run --build --rm eval python -m eval.run --documents /app/fixtures --out /app/reports --config rerank   # one configuration; comparison.md is not rewritten
```

The `eval` service is the API image plus the eval package and the fixture documents (Dockerfile
target `eval`; `--build` picks up dataset or configuration edits) and reads the same `.env`
(providers, models, keys). Only the output is mounted: reports are written here as the host user
(`EVAL_UID`/`EVAL_GID`, default 1000), so run it from a host shell (bind mounts started from the
dev container resolve on the host). Without Docker, from `backend/` with the database on
`localhost:5432`: `uv run --env-file ../.env python -m eval.run`.

## What runs

- **Dataset** — [`backend/eval/dataset.yaml`](../../backend/eval/dataset.yaml): 13 questions over
  the fixture documents (`backend/tests/fixtures/documents/`): answerable from one source (pdf,
  md, txt), from two sources (coworking), by an exact term (`US$ 250`), not covered by any
  document, and unrelated to the collection. Each answerable question lists the sources that must
  support it: file, page (PDF) or heading (Markdown), and a phrase the chunk contains.
- **Configurations** — [`backend/eval/configs.yaml`](../../backend/eval/configs.yaml). Each one
  starts from the code defaults of the RAG settings (`app/config.py`), never from the local
  `.env`, and applies its overrides; providers and models come from the environment.
- **Pipeline** — the application's own wiring (`build_container`): the real `IngestionService`
  indexes the documents and the real `AnswerQuestion` answers, against the Compose database.
  Documents are indexed under an evaluation owner derived from the embedding model and chunking,
  so they never appear in the UI and a re-run reuses them. Questions run one at a time.
- **Outputs** — `<configuration>.md` and `.json` per configuration and
  [`comparison.md`](comparison.md). Reports hold ids, file names and metrics only, never answer or
  chunk text. A question that fails (provider error, timeout) is reported as an error and the run
  goes on.

## Metrics

| Metric | Definition |
|---|---|
| Outcome accuracy | Outcome (`answered` / `insufficient_evidence`) equals the expected one |
| Retrieval hit@k | Share of expected sources among the `RETRIEVAL_TOP_K` fused chunks |
| Expected-source MRR | Mean of 1/rank of each expected source in the fused list (0 if missed); separates configurations when hit@k saturates |
| Correct refusal rate | Uncovered and unrelated questions ending as `insufficient_evidence` with no numbered source; an error never counts |
| Citation validity | Answers whose every cited chunk was retrieved for that question and matches an expected source |
| Citation recall | Share of expected sources the answer cites |
| Latency p50 / p95 | Wall time of `AnswerQuestion.answer` per question (embedding, retrieval, rerank, generation) |
| Tokens, chat cost | Chat-model tokens reported by the provider (answer and rerank calls) priced with `configs.yaml`; the query embedding is not priced |

## Results (2026-11-22, `claude-haiku-5-5`, `text-embedding-3-small`)

| Metric | baseline | rerank | small-chunks | strict-relevance |
|---|---|---|---|---|
| Outcome accuracy | 100% | 100% | 100% | 100% |
| Retrieval hit@k | 100% | 100% | 100% | 100% |
| Expected-source MRR | 0.93 | 0.93 | 0.77 | 0.93 |
| Correct refusal rate | 100% | 100% | 100% | 100% |
| Citation validity | 100% | 100% | 78% | 100% |
| Latency p50 / p95 | 1432 / 2603 ms | 2336 / 16733 ms | 1514 / 2570 ms | 1425 / 2850 ms |
| Chat tokens in / out | 14162 / 1263 | 23602 / 1772 | 14006 / 1260 | 13703 / 1270 |
| Chat cost (13 questions) | $0.0020 | $0.0032 | $0.0020 | $0.0020 |

Full tables: [`comparison.md`](comparison.md) and the per-configuration reports.

## Defaults chosen

- **Reranker off (`RERANK_ENABLED=false`).** Same quality as the baseline on every metric, for
  about 67% more chat tokens and +0.9 s at p50 (one extra chat call per question with evidence).
  With hybrid retrieval the expected sources are already ranked near the top (MRR 0.93), so the
  reranker has nothing to fix here.
- **Chunks of 1000/150 characters.** The fixture pages and sections are shorter than one chunk,
  so the default keeps each page or section whole. One-sentence chunks (120/20) split related
  sentences: the expected passage ranks lower (MRR 0.77) and answers cite neighbouring fragments
  that do not hold it (citation validity 78%).
- **`MIN_RELEVANCE=0.30`.** The unrelated questions have no chunk above 0.30, so the chat model
  is not even called (about 0.3 s, no tokens). Raising the floor to 0.45 changes no outcome, so
  there is no evidence to justify a stricter gate that could refuse paraphrased questions.

## Limits

- hit@k and MRR are measured on the fused list, before the reranker and the `MIN_RELEVANCE`
  floor, so those two configurations can only move the outcome, refusal and citation metrics.
- The collection is tiny (9 chunks at the defaults) and `RETRIEVAL_TOP_K=6`, so hit@k saturates;
  MRR and citation validity are the discriminating metrics. A larger corpus with near-duplicate
  documents is the next step before tuning `RETRIEVAL_TOP_K` or the fusion weights.
- LLM outputs are not deterministic: outcomes were stable across runs, latency and tokens vary by
  a few percent, and p95 over 13 questions is one slow provider call (rerank's 16.7 s). A
  transient provider error appears as an error row; re-run the configuration.
- Prices in `configs.yaml` are a dated snapshot; a model without a price shows the cost as `n/a`.
