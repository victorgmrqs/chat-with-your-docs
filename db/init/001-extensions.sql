CREATE EXTENSION IF NOT EXISTS vector;

-- Read-only role for the local Postgres MCP server (.mcp.json). Local development only.
CREATE ROLE cwyd_readonly LOGIN PASSWORD 'cwyd_readonly';
GRANT pg_read_all_data TO cwyd_readonly;
