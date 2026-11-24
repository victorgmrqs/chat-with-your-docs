# Source

- Upstream: https://github.com/timescale/pg-aiguide
- Path: `skills/pgvector-semantic-search`
- Commit: 1aef6e452b97fae580d57677a807fd0d601ddc7b
- License: Apache-2.0 (see `LICENSE`)
- Vendored: 2026-11-20
- Modified: yes. In accordance with Apache-2.0 section 4(b), these files were modified from the original.

## Modifications

- Narrowed `description` (removed "LLM, AI search" keywords and quantization triggers); removed `metadata`; added `## Project overrides`.
- Default column type is `vector(N)` + `vector_cosine_ops` (langchain-postgres `PGVectorStore` uses `vector(N)`); `halfvec` demoted to "verify before use".
- Session-level `SET` replaced by `SET LOCAL` inside the retrieval transaction.
- Added "Hybrid retrieval" pointer (vector + full-text fused with RRF in the app; `owner_id`/`status` filters set by the app).
- `relaxed_order` note: outer re-sort when exact ordering matters.
- RAM-capacity tables and binary quantization replaced by a short note.
- Removed pgvectorscale section and hypertable mention; performance-by-dataset-size table removed.

## Dropped files

None (upstream skill is a single SKILL.md).
