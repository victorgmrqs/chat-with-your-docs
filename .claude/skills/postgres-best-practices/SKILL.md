---
name: postgres-best-practices
description: Use when designing PostgreSQL schema, indexes or migrations, writing non-trivial SQL, or diagnosing query, lock or connection problems. Not for vector/HNSW indexes or similarity search (see pgvector-semantic-search).
license: MIT
---

## Project overrides

These project rules win over anything below.

- Database is PostgreSQL 17 + pgvector (image `pgvector/pgvector:pg17`). Extensions not in that image (for example `pg_uuidv7`) are not available.
- Access control is app-level: every query filters on `owner_id`. RLS is optional defence in depth behind that filtering, never a replacement.
- Per-request context (user id, timeouts) uses `SET LOCAL` / `set_config(..., true)` inside the transaction, never session-level `SET`.
- Server settings (`ALTER SYSTEM`, `max_connections`, timeouts) live in the config file or Docker Compose flags; the agent never runs `ALTER SYSTEM` or touches a shared database.
- Full-text search on user input uses `websearch_to_tsquery`. Bulk loads use `COPY ... FROM STDIN`.
- Behind pgbouncer (transaction mode) with asyncpg, set `statement_cache_size=0`.

# PostgreSQL Best Practices

Rules for schema design, indexing, queries, connections, locking and diagnostics, prioritized by impact. Each rule file has an incorrect and a correct SQL example.

## When to Apply

- Designing tables, choosing column types, writing migrations
- Adding or reviewing indexes
- Writing non-trivial SQL
- Diagnosing slow queries, lock waits, deadlocks or connection exhaustion

## Rule Categories by Priority

| Priority | Category | Impact | Prefix |
|----------|----------|--------|--------|
| 1 | Query Performance | CRITICAL | `query-` |
| 2 | Connection Management | CRITICAL | `conn-` |
| 3 | Security | CRITICAL | `security-` |
| 4 | Schema Design | HIGH | `schema-` |
| 5 | Concurrency & Locking | MEDIUM-HIGH | `lock-` |
| 6 | Data Access Patterns | MEDIUM | `data-` |
| 7 | Monitoring & Diagnostics | LOW-MEDIUM | `monitor-` |
| 8 | Advanced Features | LOW | `advanced-` |

## How to Use

Read the individual rule file that matches the task, for example:

```
references/query-missing-indexes.md
references/query-partial-indexes.md
references/schema-primary-keys.md
references/advanced-full-text-search.md
```

Rule files by prefix: `query-*`, `conn-*`, `security-*` (rls-basics, privileges), `schema-*`, `lock-*`, `data-*`, `monitor-*`, `advanced-*` (full-text-search, jsonb-indexing). Partitioning and RLS performance tuning are not covered here.

## References

- https://www.postgresql.org/docs/current/
- https://wiki.postgresql.org/wiki/Performance_Optimization
