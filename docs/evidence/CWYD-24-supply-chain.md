# CWYD-24 — Supply chain evidence

Evidence for the card's acceptance criteria. CI results are real GitHub Actions runs on
`victorgmrqs/chat-with-your-docs`, copied from `gh run view` and the job log. Date: 2026-11-23.

## A deliberately vulnerable pin fails the audit

Scratch branch `scratch/CWYD-24-vulnerable-pin`: this card's `ci.yml`, `osv-scanner.toml` and
`scripts/check-audit-ignores.py`, plus `lodash@4.17.20` added as a frontend dev dependency
(`npm install --package-lock-only`). Draft PR #24 against `development`,
[run 45294627717](https://github.com/victorgmrqs/chat-with-your-docs/actions/runs/45294627717).

Job steps (`dependency audit`):

```text
Accepted advisories have a reason and an expiry: success
Install osv-scanner (release binary, checksum pinned): success
Scan backend/uv.lock and frontend/package-lock.json (any known advisory fails): failure
```

Log excerpt:

```text
1 accepted advisories, 0 problems
osv-scanner: OK
Scanned .../backend/uv.lock file and found 91 packages
Scanned .../frontend/package-lock.json file and found 582 packages
GHSA-g3hv-75wg-m249 and 1 alias have been filtered out because: minimatch 10.2.6 (glob amplification DoS) is a dev-only dependency of the shadcn CLI ...
Total 1 package affected by 4 known vulnerabilities (0 Critical, 2 High, 2 Medium, 0 Low, 0 Unknown) from 1 ecosystem.
| https://osv.dev/GHSA-29mw-wpgm-hmr9 | 5.3  | npm       | lodash (dev) | 4.17.20 | 4.17.21       | frontend/package-lock.json |
| https://osv.dev/GHSA-35jh-r3h4-6jhm | 7.2  | npm       | lodash (dev) | 4.17.20 | 4.17.21       | frontend/package-lock.json |
| https://osv.dev/GHSA-r5fr-rjxr-66jc | 8.1  | npm       | lodash (dev) | 4.17.20 | 4.18.0        | frontend/package-lock.json |
| https://osv.dev/GHSA-xxjr-mmjv-4gpg | 6.9  | npm       | lodash (dev) | 4.17.20 | 4.17.23       | frontend/package-lock.json |
##[error]Process completed with exit code 1.
```

Run result:

```text
conclusion: failure
changes: success
skills drift: success
backend checks: success
frontend checks: success
dependency audit: failure  # the only failing job
image (backend): success
image (frontend): success
publish: skipped           # pull requests never publish
ci-gate: failure           # the required check blocks the merge
```

The PR was closed and the scratch branch deleted afterwards; nothing from it was merged.

## The current lockfiles pass, with one reviewed advisory

Local run of the same binary (v2.7.1, SHA-256 verified) and command on this branch:

```text
Scanned backend/uv.lock file and found 91 packages
Scanned frontend/package-lock.json file and found 581 packages
GHSA-g3hv-75wg-m249 and 1 alias have been filtered out because: ...
Filtered 1 vulnerability from output
No issues found
```

The first scan, before the exception, found GHSA-g3hv-75wg-m249 (`minimatch@10.2.6`, medium,
fixed in 11.0.1), reached only through `shadcn → ts-morph → @ts-morph/common`. It was accepted in
`osv-scanner.toml` until 2027-02-21 with its reason: dev-only, patterns are our own, not in any
image. Other `minimatch` copies are 11.0.9 (fixed) and 5.1.9 (outside the affected range).

## Accepted advisories must have a reason and an expiry

`scripts/check-audit-ignores.py` against a scratch file with one entry per rule:

```text
::error file=bad.toml::GHSA-a: ignoreUntil 2026-01-01 has been reached; fix or review it again
::error file=bad.toml::GHSA-b: missing reason
::error file=bad.toml::GHSA-b: missing ignoreUntil date
::error file=bad.toml::GHSA-c: ignoreUntil 2030-01-01 is more than 90 days away
4 accepted advisories, 4 problems          # exit 1; GHSA-d (valid, 27 days away) passes
```

## Actions pinned by SHA, enforced by the repository

All 15 `uses:` lines in `ci.yml` reference a 40-character commit SHA with a `# vX.Y.Z` comment
(`grep -c` 15 pinned, 0 unpinned). The repository Actions policy now requires it:

```text
$ gh api repos/victorgmrqs/chat-with-your-docs/actions/permissions
{"enabled":true,"allowed_actions":"all","sha_pinning_required":true}
```

## Dependabot configuration

`.github/dependabot.yml` validates against the SchemaStore `dependabot-2.0` schema (0 errors); five ecosystems: uv, npm,
docker (four Dockerfiles), docker-compose (`compose.yaml`) and github-actions.
Dependabot reads its configuration from the default branch (`main`), so the Insights check and
the first PRs against `development` happen after the next release merges `development` into
`main`: **QA after release** (Insights → Dependency graph → Dependabot shows the five ecosystems
without errors, and a PR targets `development`).
