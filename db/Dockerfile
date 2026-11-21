# Init scripts are baked in (not bind-mounted) so the stack behaves the same from the host,
# from the dev container (docker-outside-of-docker resolves bind mounts on the host) and in k8s.
FROM pgvector/pgvector:pg17
COPY init/ /docker-entrypoint-initdb.d/
