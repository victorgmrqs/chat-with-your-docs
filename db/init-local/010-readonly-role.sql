-- Read-only role for the local Postgres MCP server (.mcp.json). Local image target only:
-- never shipped in the runtime image used outside Docker Compose.
CREATE ROLE cwyd_readonly LOGIN PASSWORD 'cwyd_readonly';
GRANT pg_read_all_data TO cwyd_readonly;
