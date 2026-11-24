# Development

Working on the code: dev container, tests, the API contract, the design system, CI and images.
Setup and the design rationale are in the [README](../README.md).

## Local workflow

The repository ships a dev container (`.devcontainer/`) with Python 3.14, uv, Node 26 and access
to the host Docker daemon. Open the folder in VS Code or Cursor and choose *Reopen in Container*;
dependencies are installed on creation.

```bash
# backend/
uv run ruff check . && uv run ruff format --check .   # lint
uv run mypy .                                          # typecheck (strict)
uv run pytest                                          # unit + integration (testcontainers)
uv run pytest -m "not integration"                     # fast loop without Docker
RUN_LIVE_TESTS=1 uv run --env-file ../.env pytest -m live  # opt-in: real OpenAI/Anthropic calls
uv run --env-file ../.env uvicorn app.main:app --reload  # API on :8000; uv loads ../.env, the app does not

# frontend/
npm run lint && npm run typecheck && npm test
npm run dev                                            # Vite on :5173, /api → BACKEND_URL (default :8000)
npm run tokens:audit                                   # design tokens: no drift, no hardcoded values
npm run api:types                                      # openapi.json → src/api/schema.d.ts
VITE_API_MOCKS=true npm run dev                        # the app on MSW mocks, no backend needed
```

The frontend is typed from the API contract: `backend/scripts/export_openapi.py` writes the
FastAPI schema to `frontend/openapi.json` without starting the app, `npm run api:types` turns it
into `frontend/src/api/schema.d.ts` (both committed), and every call goes through the
openapi-fetch client in `frontend/src/api/client.ts` on the relative `/api` path. After changing
anything under `backend/app/api/`, regenerate both:
`cd backend && uv run python -m scripts.export_openapi && npm --prefix ../frontend run api:types`.
The MSW handlers used by the Vitest suite and by `VITE_API_MOCKS=true` are typed from the same
schema, so a contract change breaks the frontend typecheck instead of the running app.
`openapi-typescript` declares a TypeScript 5 peer; an `overrides` entry in `frontend/package.json`
runs it on the project's TypeScript 6.

The UI is built with Tailwind v4 and shadcn/ui on a design system extracted from the design
handoff: tokens live in `docs/design-tokens.json` (primitive → semantic → component), the theme in
`frontend/src/styles/theme.css` is generated from it (`npm run tokens:apply`), and the audit fails
on a missing token, a theme value that drifted or a hardcoded color, size or radius in `src/`.
With `npm run dev`, `http://localhost:5173/preview.html` shows every handoff screen composed from
the components with static data (dev only, not part of the build).

The chat adapter contract tests (`tests/contract/`) run both the OpenAI and the Anthropic
adapters offline against a local HTTP stub of the providers' APIs. The `live` tests call the
real APIs and are skipped unless `RUN_LIVE_TESTS=1`; they also need the provider keys and
`LIVE_OPENAI_CHAT_MODEL` / `LIVE_ANTHROPIC_CHAT_MODEL` (each provider is skipped without them).

Integration tests build `db/Dockerfile` and start it with testcontainers, so they need a Docker
daemon but not the Compose stack. To run the API outside Compose, set `DATABASE_URL` (see
`.env.example`). From the dev container, the Compose services are reached at
`host.docker.internal`, e.g. `BACKEND_URL=http://host.docker.internal:8000 npm run dev`. This
works on Docker Desktop (macOS, Windows/WSL), which forwards `host.docker.internal` to the host
loopback. On native Linux Docker Engine it resolves to the bridge gateway, which cannot reach
ports bound to `127.0.0.1`: run the Vite dev server on the host, or bind the ports you need to
the gateway address in a local `compose.override.yaml` (never commit it).

## CI and images

`.github/workflows/ci.yml` runs on every pull request to `development` or `main`:

| Job | What it does |
| --- | --- |
| `changes` | Path filter: `backend/**` and `db/**` select the backend, `frontend/**` the frontend (a change to the workflow selects both) |
| `backend checks` | The backend lint, typecheck and test commands from [Local workflow](#local-workflow), plus a check that `frontend/openapi.json` matches the API |
| `frontend checks` | The frontend lint, typecheck and test commands from [Local workflow](#local-workflow), plus a check that `src/api/schema.d.ts` matches `openapi.json` |
| `skills drift` | Always runs. Fails when a generated testing guide's copy in `.claude/skills/` drifts from its source ([Skills curation](skills-curation.md#generated-skills)) |
| `dependency audit` | Always runs. Scans `backend/uv.lock` and `frontend/package-lock.json` with [osv-scanner](https://github.com/google/osv-scanner); any known advisory fails the job unless it was [accepted after review](#accepting-a-reviewed-advisory) |
| `image (<component>)` | Builds the component's Dockerfile and scans it with Trivy; a fixable HIGH or CRITICAL vulnerability fails the job |
| `publish (<component>)` | Pushes the scanned image to GHCR (never on pull requests) |
| `ci-gate` | Always reports. Fails when any job failed or was cancelled; a job skipped by the path filter passes |

`ci-gate` is the only required status check on `development` and `main`, so a PR that touches
only the frontend is not left waiting for backend checks that never run. The path filter applies
to pull requests only; pushes, tags and manual runs check both components.

To pass the scan, the backend image applies pending Debian security updates and removes the
system pip (the app runs from the uv virtualenv), and the frontend image uses the mainline
`nginx-unprivileged:1.31-alpine` with pending Alpine updates, because the 1.30 stable image still
ships nginx with fixable vulnerabilities. CI passes a daily `UPGRADE_EPOCH` build argument, so the
upgrade layer is rebuilt once a day instead of being served from the build cache.

**Publishing.** Pushes to `development` and `main`, `v*.*.*` tags and manual runs (*Actions →
CI → Run workflow* on `development` or `main`) build both images and publish them only when
every check and both scans passed: one failure publishes nothing. The image that is pushed is
the one that was scanned. Images:

```
ghcr.io/victorgmrqs/chat-with-your-docs/backend:sha-<short commit>
ghcr.io/victorgmrqs/chat-with-your-docs/frontend:sha-<short commit>
```

Each image also gets the branch name as a moving tag (`development`, `main`) and the version on
a release tag (`1.2.0`). Each publish job writes the digest in the run summary. Deploy by
digest: it is the only immutable reference, since a later rebuild of the same commit (a release
tag, or the daily OS-upgrade refresh) pushes a new image under the same `sha-` tag. A burst of
pushes to `development` runs only the first and the last commit; the ones in between get no
images. The *Run workflow* button appears once `ci.yml` is on `main`, the default branch.

**Supply chain.** Third-party actions are pinned by full commit SHA, with the release in a
comment, and the repository's Actions policy requires SHA pinning. The audit job downloads the
osv-scanner release binary and checks it against a SHA-256 pinned in `ci.yml`. That version is
the one pin Dependabot does not cover: bump it by hand (steps in the `ci.yml` comment).
Dependabot (`.github/dependabot.yml`) checks uv, npm, Docker base images (Dockerfiles and
`compose.yaml`) and GitHub Actions every Monday and opens PRs against `development`: minor and
patch updates grouped into one PR per ecosystem, majors one PR each, each release proposed only
after Dependabot's default 3-day cooldown. These PRs go through the same checks and review as
any other. Dependabot *security* updates stay off because they always target `main`; the audit
job blocks a vulnerable dependency instead. Dependabot reads its configuration from `main`, so
it starts after the release that brings this file there.

#### Accepting a reviewed advisory

When an advisory cannot be fixed yet (no patched release) or does not apply, add it to
`osv-scanner.toml` in the same PR that explains why:

```toml
[[IgnoredVulns]]
id = "GHSA-xxxx-xxxx-xxxx"          # the ID the audit job printed
ignoreUntil = 2027-02-01            # at most 90 days away
reason = "Why it does not apply or cannot be fixed yet, and what ends the exception."
```

`scripts/check-audit-ignores.py` fails the job when an entry has no reason, no `ignoreUntil`, a
date more than 90 days away, or a date already past. An exception therefore expires, and the
advisory has to be fixed or reviewed again.

## Repository layout

```
backend/    FastAPI app (app/{domain,application,adapters,api}), Alembic migrations, tests and
            test fixtures (scripts/generate_fixtures.py), OpenAPI export
            (scripts/export_openapi.py), RAG evaluation (eval/), Dockerfile
frontend/   React + Vite SPA (src/components, src/hooks, src/api with the generated schema,
            src/mocks for MSW, src/styles/theme.css), openapi.json, token scripts
            (scripts/tokens), dev-only design preview (preview.html), nginx template, Dockerfile
db/         PostgreSQL image: init scripts for the pgvector extension; the `local` target used
            by Compose also creates the read-only role for the Postgres MCP server
docs/       design tokens, domain rules, HTTP evidence, evaluation reports, curation notes,
            homelab deploy runbook (deploy/)
scripts/    end-to-end smoke test (smoke.sh), CI helpers, docs guard
.github/    CI workflow (checks, image scan, GHCR publishing) and the PR template
compose.yaml, .env.example
```
