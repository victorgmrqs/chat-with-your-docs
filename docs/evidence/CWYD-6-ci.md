# CWYD-6 — CI and image publishing evidence

Evidence for the card's required scenarios. Every result below is a real GitHub Actions run on
`victorgmrqs/chat-with-your-docs`; job names and conclusions are copied from `gh run view`.
Workflow: `.github/workflows/ci.yml`. Date: 2026-11-22.

## container_pipeline_success

**Pull request (checks + image build + scan, no publish).** PR #7, commit `3ea3c28`,
[run 45058417017](https://github.com/victorgmrqs/chat-with-your-docs/actions/runs/45058417017):

```text
conclusion: success
changes: success
frontend checks: success
backend checks: success
image (backend): success
image (frontend): success
ci-gate: success
publish: skipped          # pull requests never publish
```

Both components show their own checks on the PR, and `ci-gate` reports the combined result.

**Authorized publish.** Publishing runs on pushes to `development`/`main`, version tags and
manual runs; the first one is the merge of PR #7 into `development`. Its run link, image
references and digests are added below after that merge (agreed at checkpoint 1: the workflow
cannot be dispatched before it exists on the default branch).

```text
TODO(CWYD-6 follow-up): publish run link
ghcr.io/victorgmrqs/chat-with-your-docs/backend:sha-<short>   @sha256:<digest>
ghcr.io/victorgmrqs/chat-with-your-docs/frontend:sha-<short>  @sha256:<digest>
```

## container_pipeline_checks_failed

**A failed check blocks image build and publishing.** Throwaway PR #8 (closed without merging,
branch deleted) added a deliberately failing backend test, commit `3dae7c7`,
[run 45058419885](https://github.com/victorgmrqs/chat-with-your-docs/actions/runs/45058419885).
The first check to reject it was mypy strict, before pytest ran:

```text
tests/unit/test_ci_failure_proof.py:5: error: Non-overlapping equality check (left operand type: "Literal[1]", right operand type: "Literal[2]")  [comparison-overlap]
Found 1 error in 1 file (checked 55 source files)
##[error]Process completed with exit code 1.

conclusion: failure
changes: success
backend checks: failure
frontend checks: success
image: skipped            # no image is built after a failed check
publish: skipped
ci-gate: failure
```

**A failed scan blocks publishing.** The first run on PR #7, commit `de4f6d6`,
[run 45057457625](https://github.com/victorgmrqs/chat-with-your-docs/actions/runs/45057457625),
passed every check and failed both scans on real vulnerabilities in the base images:

```text
conclusion: failure
changes: success
backend checks: success
frontend checks: success
image backend: failure    # zlib1g HIGH (debian 13.7); msgpack, setuptools, urllib3 HIGH vendored in the system pip
image frontend: failure   # 5 CRITICAL, 15 HIGH (nginx 1.30.6, musl, brotli, expat, libxml2, zlib, curl)
ci-gate: failure
publish: skipped
```

Fix (commit `8f28623`): the backend runtime stage upgrades its Debian packages and removes
the unused system pip (the app runs from the uv venv); the frontend moved to the nginx 1.31
mainline image and upgrades its Alpine packages. Both images pass the scan in run 45058417017
above, and `docker compose up --build --wait` reaches healthy for db, backend and frontend, with
`/`, `/api/health/ready` (through nginx) and `:8000/health/ready` answering 200.

## Required check

`ci-gate` was added as a required status check (GitHub Actions app only) to the
`protect-development` and `protect-main` rulesets with `gh api`. PR #7 then reported
`mergeStateStatus: CLEAN` with `ci-gate: SUCCESS`.
