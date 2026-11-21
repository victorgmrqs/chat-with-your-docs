# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Every entry links its Jira card.

## [Unreleased]

### Added

- Monorepo scaffold (React + Vite, FastAPI with uv) and a one-command local stack: `docker compose up
  --build --wait` starts PostgreSQL + pgvector, the API and the web app, each gated on a health
  check (`/health`, `/health/ready`); startup fails fast naming every missing configuration variable;
  one command each for lint, typecheck and test
  ([CWYD-2](https://goncalvesmarques.atlassian.net/browse/CWYD-2)).

### Maintenance

- AI-assisted development foundation: workflow configuration, path-scoped rules, 10 curated and
  security-reviewed skills plus 1 original, read-only Postgres and Context7 MCP servers, and protected
  `main`/`development` branches ([CWYD-9](https://goncalvesmarques.atlassian.net/browse/CWYD-9)).
