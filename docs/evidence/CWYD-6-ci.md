# CWYD-6 — CI and image publishing evidence

Evidence for the card's required scenarios. Every result below is a real GitHub Actions run on
`victorgmrqs/chat-with-your-docs`; job names and conclusions are copied from `gh run view`.
Workflow: `.github/workflows/ci.yml`. Date: 2026-11-22.

## container_pipeline_success

**Pull request (checks + image build + scan, no publish).** PR #7, commit `f610d3b`,
[run 45061035544](https://github.com/victorgmrqs/chat-with-your-docs/actions/runs/45061035544):

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

**Authorized publish.** A version tag is one of the publishing events, so the publish path was
proven before merge with a throwaway tag `v0.0.0-ci.2` on the same commit `f610d3b`
([run 45061037872](https://github.com/victorgmrqs/chat-with-your-docs/actions/runs/45061037872)).
The tag was deleted afterwards; the image versions stay in GHCR. Job results and the publish
jobs' summary (digests as reported by the registry on push):

```text
conclusion: success
changes: success
backend checks: success
frontend checks: success
image (backend): success
image (frontend): success
publish (backend): success
publish (frontend): success
ci-gate: success

### backend
- Digest: `ghcr.io/victorgmrqs/chat-with-your-docs/backend@sha256:0b1f8edf855a297e6659bb0d55b342f23d374997c6921eef4ad823f5690d4ab7`
- Tag: `ghcr.io/victorgmrqs/chat-with-your-docs/backend:0.0.0-ci.2`
- Tag: `ghcr.io/victorgmrqs/chat-with-your-docs/backend:sha-f610d3b`
### frontend
- Digest: `ghcr.io/victorgmrqs/chat-with-your-docs/frontend@sha256:b63e9c653605ce9bc0382aa6d0a5212252a9e9f670bdcb525911b28bc1e4717f`
- Tag: `ghcr.io/victorgmrqs/chat-with-your-docs/frontend:0.0.0-ci.2`
- Tag: `ghcr.io/victorgmrqs/chat-with-your-docs/frontend:sha-f610d3b`
```

Two independent images, each with a commit tag (`sha-f610d3b`) and a digest. The first publish
from `development` happens when PR #7 merges.

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
mainline image and upgrades its Alpine packages. Both images pass the scan in run 45061035544
above, and `docker compose up --build --wait` reaches healthy for db, backend and frontend, with
`/`, `/api/health/ready` (through nginx) and `:8000/health/ready` answering 200.

## Required check

`ci-gate` was added as a required status check (GitHub Actions app only) to the
`protect-development` and `protect-main` rulesets with `gh api`. PR #7 then reported
`mergeStateStatus: CLEAN` with `ci-gate: SUCCESS`.
