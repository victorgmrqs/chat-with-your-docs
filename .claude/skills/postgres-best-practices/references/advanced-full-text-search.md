---
title: Use tsvector for Full-Text Search
impact: MEDIUM
impactDescription: 100x faster than LIKE, with ranking support
tags: full-text-search, tsvector, gin, search
---

## Use tsvector for Full-Text Search

LIKE with wildcards can't use indexes. Full-text search with tsvector is orders of magnitude faster.

**Incorrect (LIKE pattern matching):**

```sql
-- Cannot use index, scans all rows
select * from articles where content like '%postgresql%';

-- Case-insensitive makes it worse
select * from articles where lower(content) like '%postgresql%';
```

**Correct (full-text search with tsvector):**

```sql
-- Add tsvector column and index
alter table articles add column search_vector tsvector
  generated always as (to_tsvector('english', coalesce(title,'') || ' ' || coalesce(content,''))) stored;

create index articles_search_idx on articles using gin (search_vector);

-- Fast full-text search
select * from articles
where search_vector @@ websearch_to_tsquery('english', 'postgresql performance');

-- With ranking
select *, ts_rank(search_vector, query) as rank
from articles, websearch_to_tsquery('english', 'postgresql') query
where search_vector @@ query
order by rank desc;
```

Use `websearch_to_tsquery` for end-user input: it never raises a syntax error on arbitrary text. `to_tsquery` throws on unbalanced quotes, stray `&`, `:` etc., so only feed it trusted, already-built query strings.

```sql
-- AND: all terms required (default)
websearch_to_tsquery('english', 'postgresql performance')

-- OR: either term
websearch_to_tsquery('english', 'postgresql or mysql')

-- Phrase and exclusion
websearch_to_tsquery('english', '"query planner" -mysql')

-- Prefix matching (trusted input only, uses to_tsquery)
to_tsquery('english', 'post:*')
```

In hybrid retrieval, full-text results are fused with vector results in the application (RRF); keep `owner_id`/`status` filters in the same query.

Reference: [Full Text Search](https://www.postgresql.org/docs/current/textsearch.html)
