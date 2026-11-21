---
title: Batch INSERT Statements for Bulk Data
impact: MEDIUM
impactDescription: 10-50x faster bulk inserts
tags: batch, insert, bulk, performance, copy
---

## Batch INSERT Statements for Bulk Data

Individual INSERT statements have high overhead. Batch multiple rows in single statements or use COPY.

**Incorrect (individual inserts):**

```sql
-- Each insert is a separate transaction and round trip
insert into events (user_id, action) values (1, 'click');
insert into events (user_id, action) values (1, 'view');
insert into events (user_id, action) values (2, 'click');
-- ... 1000 more individual inserts

-- 1000 inserts = 1000 round trips = slow
```

**Correct (batch insert):**

```sql
-- Multiple rows in single statement
insert into events (user_id, action) values
  (1, 'click'),
  (1, 'view'),
  (2, 'click'),
  -- ... up to ~1000 rows per batch
  (999, 'view');

-- One round trip for 1000 rows
```

For large imports, use COPY:

```sql
-- COPY ... FROM STDIN is fastest and works from the application (client-side data).
-- Do not use COPY FROM '/path/file': it reads server-side files and needs superuser/pg_read_server_files.
copy events (user_id, action) from stdin with (format csv);
1,click
1,view
2,click
\.
```

From Python, stream rows through the driver's COPY support (asyncpg `copy_records_to_table`, psycopg `cursor.copy`) instead of building SQL strings.

Reference: [COPY](https://www.postgresql.org/docs/current/sql-copy.html)
