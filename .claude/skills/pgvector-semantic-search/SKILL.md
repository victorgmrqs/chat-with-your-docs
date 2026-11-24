---
name: pgvector-semantic-search
description: Use when storing or searching vector embeddings in PostgreSQL with pgvector, creating HNSW or IVFFlat indexes, or tuning recall and filtered vector search. Not for general schema or SQL work (see postgres-best-practices).
license: Apache-2.0
compatibility: Requires PostgreSQL 15+ with the pgvector extension
---

## Project overrides

These project rules win over anything below.

- Stack: PostgreSQL 17 (`pgvector/pgvector:pg17`), `langchain-postgres` `PGEngine` / `PGVectorStore`. Domain and use cases never touch SQL or LangChain; vector search lives in the retrieval adapter.
- `PGVectorStore` creates `vector(N)` columns. Use `vector` + `vector_cosine_ops` unless we own the SQL and have verified `halfvec` support end to end.
- Retrieval is hybrid: vector search plus full-text (`websearch_to_tsquery`), fused with RRF in the app. Filters (`owner_id`, `status = ready`) are applied by the app on every query.
- Per-query settings (`hnsw.ef_search`, `hnsw.iterative_scan`, `hnsw.max_scan_tuples`) use `SET LOCAL` inside the retrieval transaction, never session-level `SET` (pooled connections leak it).
- No pgvectorscale, no hypertables.

# pgvector for Semantic Search

Semantic search finds content by meaning rather than exact keywords. An embedding model converts text into high-dimensional vectors, where similar meanings map to nearby points. pgvector stores these vectors in PostgreSQL and uses approximate nearest neighbor (ANN) indexes to find the closest matches quickly. Store your text alongside its embedding, then query by converting your search text to a vector and returning the rows with the smallest distance.

This guide covers pgvector setup and tuning, not embedding model selection or text chunking, which significantly affect search quality. Iterative scan needs pgvector 0.8.0+.

## Golden Path (Default Setup)

Use this configuration unless you have a specific reason not to.
- Embedding column data type: `vector(N)` where `N` is your embedding dimension (must match everywhere). Examples use 1536; replace with your dimension `N`.
- Distance: cosine (`<=>`)
- Index: HNSW (`m = 16`, `ef_construction = 64`) with `vector_cosine_ops`, queried with `<=>`.
- Query-time recall: `SET LOCAL hnsw.ef_search = 100` inside the query transaction (a good starting point, increase for higher recall at higher latency)
- Query pattern: `ORDER BY embedding <=> $1::vector(N) LIMIT k`

## Core Rules

- **Enable the extension** in each database: `CREATE EXTENSION IF NOT EXISTS vector;`
- **Use HNSW indexes by default**: superior speed-recall tradeoff, can be created on empty tables, no training step required. Only consider IVFFlat for write-heavy or memory-bound workloads.
- **Index after bulk loading** initial data for best build performance.
- **Create indexes concurrently** in production: `CREATE INDEX CONCURRENTLY ...`
- **Use cosine distance by default** (`<=>`): for unit-normalized embeddings, cosine and inner product yield identical rankings; default to cosine.
- **Match query operator to index ops**: `vector_cosine_ops` requires `<=>`; `vector_l2_ops` requires `<->`; mismatched operators won't use the index.
- **Always cast query vectors explicitly** (`$1::vector(N)`) to avoid implicit-cast failures in prepared statements.
- **Always use the same embedding model for data and queries**.

## Type Rules

- `langchain-postgres` `PGVectorStore` stores embeddings as `vector(N)`; do not change the column type behind its back.
- `halfvec(N)` halves storage and index size with minimal recall loss, but only use it if we own the SQL and have verified support (store, index ops `halfvec_cosine_ops`, query casts `::halfvec(N)`) before adopting it.
- Do not mix `vector` / `halfvec` / `bit` without explicit casts.
- Dimensions must match: a `vector(1536)` column requires query vectors cast as `::vector(1536)`.

## Standard Pattern

```sql
CREATE TABLE items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  contents TEXT NOT NULL,
  embedding vector(1536) NOT NULL  -- NOT NULL requires embeddings generated before insert, not async
);
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops);

-- Query: returns 10 closest items. $1 is the embedding of your search text.
SELECT id, contents FROM items ORDER BY embedding <=> $1::vector(1536) LIMIT 10;
```

For other distance operators (L2, inner product, etc.), see the [pgvector README](https://github.com/pgvector/pgvector).

## Hybrid retrieval

Vector search alone misses exact terms (names, codes). We combine it with PostgreSQL full-text search (`tsvector` + `websearch_to_tsquery`) and fuse the two ranked lists with Reciprocal Rank Fusion in the application. Both queries apply the same app-set filters (`owner_id`, `status`). See the `postgres-best-practices` skill (`advanced-full-text-search`) for the full-text side.

## HNSW Index

The recommended index type. Creates a multilayer navigable graph with superior speed-recall tradeoff. Can be created on empty tables (no training step required).

```sql
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops);

-- With tuning parameters
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

### HNSW Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `m` | 16 | Max connections per layer. Higher = better recall, more memory |
| `ef_construction` | 64 | Build-time candidate list. Higher = better graph quality, slower build |
| `hnsw.ef_search` | 40 | Query-time candidate list. Higher = better recall, slower queries. Should be ≥ LIMIT. |

**ef_search tuning (rough guidelines—actual results vary by dataset):**

| ef_search | Approx Recall | Relative Speed |
|-----------|---------------|----------------|
| 40 | lower (~95% on some benchmarks) | 1x (baseline) |
| 100 | higher  | ~2x slower |
| 200 | very-high | ~4x slower |
| 400 | near-exact | ~8x slower |

```sql
-- Set for a single query (inside the retrieval transaction; session-level SET leaks on pooled connections)
BEGIN;
SET LOCAL hnsw.ef_search = 100;
SELECT id, contents FROM items ORDER BY embedding <=> $1::vector(1536) LIMIT 10;
COMMIT;
```


## IVFFlat Index (Generally Not Recommended)

Default to HNSW. Use IVFFlat only when HNSW’s operational costs matter more than peak recall.

Choose IVFFlat if:
- Write-heavy or constantly changing data AND you're willing to rebuild the index frequently
- You rebuild indexes often and want predictable build time and memory usage
- Memory is tight and you cannot keep an HNSW graph mostly resident
- Data is partitioned or tiered, and this index lives on colder partitions

Avoid IVFFlat if you need:
- highest recall at low latency
- minimal tuning
- a “set and forget” index

Notes:
- IVFFlat requires data to exist before index creation.
- Recall depends on `lists` and `ivfflat.probes`; higher probes = better recall, slower queries.

Starter config:
```sql
CREATE INDEX ON items
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 1000);

SET LOCAL ivfflat.probes = 10;  -- inside the query transaction
```


## Memory and Quantization (short note)

- If p95/p99 latency rises while CPU is mostly idle, the HNSW index is likely no longer resident in memory: add RAM, reduce `m`/`ef_construction`, or partition first.
- `halfvec` (only if verified, see Type Rules) halves index size. Binary quantization with re-ranking exists for very large datasets (10M+ vectors) and is out of scope for this project's expected size; do not adopt it without asking.
- Estimate HNSW footprint at roughly 4-6 KB per 1536-dim vector (order of magnitude) and validate by monitoring cache residency under load.


## Filtering Best Practices

Filtered vector search requires care. Depending on filter selectivity and query shape, filters can cause early termination (too few rows, missing results) or increase work (latency).


### Iterative scan (recommended when filters are selective)

By default, HNSW may stop early when a WHERE clause is present, which can lead to fewer results than expected. Iterative scan allows HNSW to continue searching until enough filtered rows are found.

Enable iterative scan when filters materially reduce the result set.

```sql
-- Enable iterative scans for filtered queries (inside the retrieval transaction)
BEGIN;
SET LOCAL hnsw.iterative_scan = relaxed_order;

SELECT id, contents
FROM items
WHERE owner_id = $2
ORDER BY embedding <=> $1::vector(1536)
LIMIT 10;
COMMIT;
```

`relaxed_order` can return results slightly out of distance order. If exact ordering matters, wrap the query and re-sort in an outer query:

```sql
SELECT * FROM (
  SELECT id, contents, embedding <=> $1::vector(1536) AS distance
  FROM items
  WHERE owner_id = $2
  ORDER BY embedding <=> $1::vector(1536)
  LIMIT 10
) t
ORDER BY distance;
```

If results are still sparse, increase the scan budget:

```sql
SET LOCAL hnsw.max_scan_tuples = 50000;  -- inside the same transaction
```

Trade-off: increasing `hnsw.max_scan_tuples` improves recall but can significantly increase latency.

**When iterative scan is not needed:**
- The filter matches a large portion of the table (low selectivity)
- You are prefiltering via a B-tree index
- You are querying a single partition or partial index


### Choose the right filtering strategy

**Highly selective filters (under ~10k rows)**
Use a B-tree index on the filter column so Postgres can prefilter before ANN.

```sql
CREATE INDEX ON items (category_id);
```

**Low-cardinality filters (few distinct values)**
Use partial HNSW indexes per filter value.

```sql
CREATE INDEX ON items
USING hnsw (embedding vector_cosine_ops)
WHERE category_id = 11;
```

**Many filter values or large datasets**
Partition by the filter key to keep each ANN index small.

```sql
CREATE TABLE items (
  embedding vector(1536),
  category_id int
) PARTITION BY LIST (category_id);
```

### Key rules

- Filters that match few rows require prefiltering, partitioning, or iterative scan.
- Always validate filtered queries by measuring p95/p99 latency and tuples visited under realistic load.



## Bulk Loading

```sql
-- COPY is fastest; binary format is faster but requires proper encoding
-- Text format: '[0.1, 0.2, ...]'
COPY items (contents, embedding) FROM STDIN;
-- Binary format (if your client supports it):
COPY items (contents, embedding) FROM STDIN WITH (FORMAT BINARY);

-- Add indexes AFTER loading (session-level SET is fine on a dedicated maintenance connection)
SET maintenance_work_mem = '4GB';
SET max_parallel_maintenance_workers = 7;
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops);
```


## Maintenance

- **VACUUM regularly** after updates/deletes—stale entries may persist until vacuumed
- **REINDEX** if performance degrades after high churn (rebuilds the graph from scratch)
- For write-heavy workloads with frequent deletes, consider IVFFlat or partitioning


## Monitoring & Debugging

```sql
-- Check index size
SELECT pg_size_pretty(pg_relation_size('items_embedding_idx'));

-- Debug query performance
EXPLAIN (ANALYZE, BUFFERS) SELECT id, contents FROM items ORDER BY embedding <=> $1::vector(1536) LIMIT 10;

-- Monitor index build progress
SELECT phase, round(100.0 * blocks_done / nullif(blocks_total, 0), 1) AS "%" 
FROM pg_stat_progress_create_index;

-- Compare approximate vs exact recall
BEGIN;
SET LOCAL enable_indexscan = off;  -- Force exact search
SELECT id, contents FROM items ORDER BY embedding <=> $1::vector(1536) LIMIT 10;
COMMIT;

-- Force index use for debugging
BEGIN;
SET LOCAL enable_seqscan = off;
SELECT id, contents FROM items ORDER BY embedding <=> $1::vector(1536) LIMIT 10;
COMMIT;
```

## Common Issues (Symptom → Fix)

| Symptom | Likely Cause | Fix |
|--------|--------------|-----|
| Query does not use ANN index | Missing `ORDER BY` + `LIMIT`, operator mismatch, or implicit casts | Use `ORDER BY` with a distance operator that matches the index ops class; explicitly cast query vectors |
| Fewer results than expected (filtered query) | HNSW stops early due to filter | Enable iterative scan; increase `hnsw.max_scan_tuples`; or prefilter (B-tree), use partial indexes, or partition |
| Fewer results than expected (unfiltered query) | ANN recall too low | Increase `hnsw.ef_search` |
| High latency with low CPU usage | HNSW index not resident in memory | Reduce `m`/`ef_construction`, add RAM, or partition |
| Slow index builds | Insufficient build memory or parallelism | Increase `maintenance_work_mem` and `max_parallel_maintenance_workers`; build after bulk load |
| Out-of-memory errors | Index too large for available RAM | Reduce index parameters or add RAM |
| Zero or missing results | NULL or zero vectors | Avoid NULL embeddings; do not use zero vectors with cosine distance |
