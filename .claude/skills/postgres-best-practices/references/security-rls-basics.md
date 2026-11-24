---
title: Row Level Security as Defence in Depth
impact: CRITICAL
impactDescription: Database-enforced tenant isolation, prevent data leaks
tags: rls, row-level-security, multi-tenant, security
---

## Row Level Security as Defence in Depth

In this project, per-owner access is enforced by the application (every query filters on `owner_id`). RLS is an optional second layer behind that filtering: it limits the damage of a missed filter, it does not replace it. Adopt it only when the extra complexity (per-transaction context, non-owner DB role) is justified.

**Incorrect (application-level filtering only):**

```sql
-- Relying on a hand-written filter that can be forgotten
select * from orders where user_id = $current_user_id;

-- Bug or bypass means all data is exposed!
select * from orders;  -- Returns ALL orders
```

**Correct (database-enforced RLS):**

```sql
-- Enable RLS on the table
alter table orders enable row level security;

-- Create policy for users to see only their orders
create policy orders_user_policy on orders
  for all
  using (user_id = current_setting('app.current_user_id')::bigint);

-- The application connects with a role that does NOT own the table and has no BYPASSRLS

-- Force RLS even for table owners
alter table orders force row level security;

-- Set user context for the current transaction only (pooler-safe, never leaks to the next client)
begin;
select set_config('app.current_user_id', '123', true);  -- true = local to this transaction
select * from orders;  -- Only returns orders for user 123
commit;
```

Never use a session-level `set` for the tenant/user context: pooled connections are reused and the value would leak to the next request.

Reference: [Row Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
