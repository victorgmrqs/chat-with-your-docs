# CWYD-6 — CI and image publishing evidence

Evidence for the card's required scenarios. Every result below is a real GitHub Actions run on
`victorgmrqs/chat-with-your-docs`; job names and conclusions are copied from `gh run view`.
Workflow: `.github/workflows/ci.yml`. Date: 2026-11-22.

## container_pipeline_success

**Pull request (checks + image build + scan, no publish).** PR #7, commit `d20a483`,
[run 45062100972](https://github.com/victorgmrqs/chat-with-your-docs/actions/runs/45062100972):

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
proven before merge with a throwaway tag `v0.0.0-ci.3` on the same commit `d20a483`
([run 45062098692](https://github.com/victorgmrqs/chat-with-your-docs/actions/runs/45062098692)).
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
- Digest: `ghcr.io/victorgmrqs/chat-with-your-docs/backend@sha256:e6b4956735a48828cfc922f1a22803a28accf0f5f38abe9f12beb6937e483d89`
- Tag: `ghcr.io/victorgmrqs/chat-with-your-docs/backend:0.0.0-ci.3`
- Tag: `ghcr.io/victorgmrqs/chat-with-your-docs/backend:sha-d20a483`
### frontend
- Digest: `ghcr.io/victorgmrqs/chat-with-your-docs/frontend@sha256:2aa0f0ed1b42f3b808ed1965cfb58785f0cefdeb6cfb6628a7bbf4b3cac1516d`
- Tag: `ghcr.io/victorgmrqs/chat-with-your-docs/frontend:0.0.0-ci.3`
- Tag: `ghcr.io/victorgmrqs/chat-with-your-docs/frontend:sha-d20a483`
```

Two independent images, each with a commit tag (`sha-d20a483`) and a digest. The first publish
from `development` happens when PR #7 merges.

**A failed push fails the publish job.** Every step runs under `shell: bash`
(`bash -e -o pipefail`, as the publish job log shows), so a `docker push` that fails on the left
of `| tee push.log` fails the step, and an empty digest is rejected explicitly. Local check of
the shell semantics with a push that is denied:

```text
$ bash -e -c 'push | tee push.log; echo "step continued"'            # implicit default before the fix
denied: permission_denied: write_package
step continued
bash -e -> exit 0
$ bash -eo pipefail -c 'push | tee push.log; echo "step continued"'  # shell: bash
denied: permission_denied: write_package
bash -eo pipefail -> exit 1
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

**A failed scan blocks publishing.** The first run on PR #7, commit `2e70d0a` (the images were
tagged `sha-de4f6d6`, the PR merge commit),
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
mainline image and upgrades its Alpine packages. Both images pass the scan in run 45062100972
above, and `docker compose up --build --wait` reaches healthy for db, backend and frontend, with
`/`, `/api/health/ready` (through nginx) and `:8000/health/ready` answering 200.

## Required check

`ci-gate` was added as a required status check (GitHub Actions app only) to the
`protect-development` and `protect-main` rulesets with `gh api`. PR #7 then reported
`mergeStateStatus: CLEAN` with `ci-gate: SUCCESS`.
