# CWYD-8 — submission review

## submission_review_success (2026-11-24)

Fresh clone of the public repository, following the README's Quick setup word for word. The
setup commands are the same on `development` and on the CWYD-8 branch.

```text
$ git clone --branch development https://github.com/victorgmrqs/chat-with-your-docs.git cwyd-clean
$ git log --oneline -1
480aa74 fix(CWYD-29): keep the documents sidebar within its column (#27)
$ cp <local .env with CHAT_PROVIDER=anthropic, CHAT_MODEL, OPENAI_API_KEY, ANTHROPIC_API_KEY> .env
$ docker compose up --build --wait          # exit 0 after 111 s, nothing cached for this project
 Container cwyd-clean-db-1 Healthy
 Container cwyd-clean-backend-1 Healthy
 Container cwyd-clean-frontend-1 Healthy

$ scripts/smoke.sh http://localhost:8080    # exit 0
== readiness
{"status":"ready","pgvector":"0.8.7"}
== upload
remote-work-policy.pdf -> 562cc0bd-ac4c-4ff8-9e2f-5842363d3dd7
expense-policy.pdf -> 8bd27f19-39e1-47e2-a3e0-01babfcbfe34
parental-leave-policy.md -> e1fc4f0a-dd8a-4853-bda5-c3d0280a7d62
== indexing
562cc0bd-ac4c-4ff8-9e2f-5842363d3dd7 ready
8bd27f19-39e1-47e2-a3e0-01babfcbfe34 ready
e1fc4f0a-dd8a-4853-bda5-c3d0280a7d62 ready
== coworking_two_sources
outcome=answered sources=expense-policy.pdf remote-work-policy.pdf
ok
== leave_split_not_covered
outcome=insufficient_evidence sources=
ok
SMOKE OK (http://localhost:8080)
```

The README's "Try it" questions, asked through the web server on the same stack:

```text
Can I work from a coworking space, and what is the monthly reimbursement limit?
  outcome=answered sources=['remote-work-policy.pdf', 'expense-policy.pdf']
What is the parental leave policy for contractors?
  outcome=answered sources=['parental-leave-policy.md']
```

The second question was the README's first draft of the insufficient-evidence example. It is
answered (the policy says it covers full-time employees only, with a citation), as
`backend/tests/fixtures/rag_cases.json` expects. The README now uses `leave_split_not_covered`,
the case the smoke test proves above.

## Links

- Relative links and anchors in `README.md`, `docs/operations.md`, `docs/development.md`,
  `docs/deploy/homelab.md` and `frontend/README.md`: all resolve, the three CWYD-8 screenshots
  included (checked by script).
- External: `https://github.com/google/osv-scanner` 200. The Jira link to CWYD-28 in
  `docs/operations.md` needs a login on a private site; it is traceability, not required reading.
- Repository `victorgmrqs/chat-with-your-docs`: public, default branch `main`. GHCR images
  `backend` and `frontend`: anonymous pull token 200.
- The README the evaluator sees is the one on `main`, so this card reaches them only after the
  `development` → `main` release.

## Content moved without loss

Every line of the old README's operational sections (Configuration to Repository layout) is
present in `docs/operations.md` or `docs/development.md`, with relative links rewritten for the
new location (checked by script). Intended differences: the RAG quality table, rebuilt in the
README from the latest `docs/eval/comparison.md` (the old one predated CWYD-21); the "Homelab
deploy" paragraph, now the README's Further reading row and the smoke-test line in Quick setup;
and the anchor `#development`, now `#local-workflow` in `docs/development.md`.

## Screenshots and video

Captured by Victor on 2026-11-24 with the browser's page capture (no address bar, extensions or
profile), so no homelab hostname appears:

| File | Shows |
|---|---|
| [`answer-two-sources.png`](CWYD-8/answer-two-sources.png) | An answer citing `remote-work-policy.pdf` (pages 1 and 2) and `expense-policy.pdf` (page 2), with the cited documents highlighted in the sidebar |
| [`not-enough-evidence.png`](CWYD-8/not-enough-evidence.png) | "Can parental leave be split into several separate periods?": not enough evidence, with the closest passage marked as not answering; the sidebar also shows an upload rejection (`empty.txt`) |
| [`indexing.png`](CWYD-8/indexing.png) | A collection with one document indexing, eight ready, and `scanned-notice.pdf` failed with its reason |

The trace of each outcome is in [`docs/evidence/CWYD-12/`](CWYD-12/), already embedded in the
README's Observability section. The demo video was moved out of CWYD-8's scope on 2026-11-24 and is
tracked by [CWYD-30](https://goncalvesmarques.atlassian.net/browse/CWYD-30), which records it and
adds the link to the README.
