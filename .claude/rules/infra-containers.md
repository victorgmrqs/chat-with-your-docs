---
paths:
  - "compose.yaml"
  - "**/Dockerfile"
  - "db/**"
  - "frontend/nginx/**"
  - ".devcontainer/**"
---

# Containers and local stack

- Base images use an explicit version tag (`python:3.14-slim-trixie`, `node:26-alpine`,
  `nginxinc/nginx-unprivileged:1.31-alpine`, `pgvector/pgvector:pg17`, `uv:0.13.7`); never
  `latest` or a bare name.
- Runtime images run as a non-root user (backend uid 10001, nginx-unprivileged on 8080).
  Multi-stage builds: build tools and dev dependencies never reach the final stage
  (`uv sync --locked --no-dev`, `npm ci` only in the build stage).
- Files a service needs at start (init SQL, nginx templates) are copied into the image, not
  bind-mounted: from the dev container (docker-outside-of-docker) bind mounts resolve on the
  host and silently mount empty directories.
- Every service has a healthcheck that proves it can serve (backend: `/health/ready`), and
  dependents use `depends_on: condition: service_healthy`. `docker compose up --build --wait`
  must return only when the stack works.
- Published ports bind to `127.0.0.1`. Services talk over the Compose network by service name
  (`db`, `backend`), never `localhost`.
- Runtime configuration comes from environment variables resolved at container start (nginx
  `BACKEND_URL` via envsubst templates), so one image serves Compose, homelab and cloud.
- Secrets only from `.env` (optional `env_file`, never committed). Compose defaults are allowed
  only for local-only values (`POSTGRES_*`). Every new variable is added to `.env.example` and
  the README configuration table in the same change.
- Env files do not strip inline comments: comments stay on their own lines.
- `db/Dockerfile` has two targets: `runtime` (default; `db/init/`, extensions only) and `local`
  (Compose; adds `db/init-local/`, the read-only MCP role). Dev-only objects never go in
  `db/init/`. Init scripts run only on an empty volume: changes need `docker compose down -v`.
- Each Dockerfile has a `.dockerignore` excluding `.venv`, `node_modules`, `dist`, caches and
  `.env*`.
