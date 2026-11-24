# Source

- Upstream: https://github.com/supabase/agent-skills
- Path: `skills/supabase-postgres-best-practices`
- Commit: c9be0e931b7930f7d02126d04774d904c381e7d7
- License: MIT (see `LICENSE`)
- Vendored: 2026-11-20
- Modified: yes

## Modifications

- Renamed to `postgres-best-practices`; removed Supabase branding, metadata block and supabase.com links (replaced with postgresql.org docs).
- New narrowed `description`; removed `metadata`; added `## Project overrides`; SKILL.md index fixed for removed files.
- `security-rls-basics`: RLS is optional defence in depth behind app-level `owner_id` filtering; `auth.uid()` replaced by `set_config(..., true)` (transaction-local).
- `conn-*`: `ALTER SYSTEM` replaced by config file / Compose flags (never run by the agent); asyncpg `statement_cache_size=0` behind pgbouncer.
- `advanced-full-text-search`: `websearch_to_tsquery` for user input.
- `data-batch-inserts`: `COPY ... FROM STDIN` only.
- `schema-primary-keys`: `pg_uuidv7` not in the image; application-generated UUIDv7.
- `lock-short-transactions`, `lock-deadlock-prevention`: `SET LOCAL` / config file instead of session `SET`.

## Dropped files

- `CHANGELOG.md`
- `references/_contributing.md`, `references/_template.md`, `references/_sections.md`
- `references/security-rls-performance.md`
- `references/schema-partitioning.md`
