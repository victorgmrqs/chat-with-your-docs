---
paths:
  - "backend/app/api/**"
  - "backend/app/main.py"
---

# Backend API conventions

- One `APIRouter` per resource with `prefix` and `tags`, registered in `create_app`
  (`app.include_router(...)`). Collection paths are `""`, not `"/"`, so `/health` does not
  redirect (307) to `/health/`.
- Routes carry no `/api` prefix: nginx (`/api/` → `${BACKEND_URL}/`) and the Vite dev proxy
  strip it. The browser always calls `/api/...`.
- Every route declares a Pydantic response DTO as its return type; closed value sets use
  `Literal` (`status: Literal["ok"]`). Never return bare dicts or ORM objects.
- Dependencies come through `Annotated[T, Depends(...)]`; no module-level globals.
- Routes never import SQLAlchemy or driver exceptions. Adapters translate connection failures
  into a typed exception (`DatabaseUnavailable`); the route maps it to `503` with a short,
  stable lowercase `detail` (`"database unavailable"`), chained with `from exc`. Programming
  errors (SQL syntax, `ProgrammingError`, bugs) are not caught: they surface as 500 and in tests.
- `detail` never carries exception text, SQL, provider messages or document content.
- Liveness (`/health`) does no I/O. Readiness (`/health/ready`) checks every hard dependency
  and is what Compose, k8s probes and the frontend `depends_on` wait on.
- New or changed routes get an entry in `docs/http/<card>.http` with the expected response.

- Reference implementation: `ready()` in `backend/app/api/health.py`.
