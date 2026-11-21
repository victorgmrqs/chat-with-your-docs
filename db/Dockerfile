# Init scripts are baked in (not bind-mounted) so the stack behaves the same from the host,
# from the dev container (docker-outside-of-docker resolves bind mounts on the host) and in k8s.

# local: Docker Compose on a developer machine; adds the read-only role for the MCP server.
FROM pgvector/pgvector:pg17 AS local
COPY init/ init-local/ /docker-entrypoint-initdb.d/

# runtime (default target): extensions only, for any shared environment.
FROM pgvector/pgvector:pg17 AS runtime
COPY init/ /docker-entrypoint-initdb.d/
