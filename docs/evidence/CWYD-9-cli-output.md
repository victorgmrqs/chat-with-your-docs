# CWYD-9 — CLI evidence

Evidence for the card's required scenarios. Outputs are verbatim; nothing is mocked.

## ai_foundation_branch_protected

Probe from a throwaway clone: an empty commit pushed directly to the protected branches, then a
branch deletion. All three are rejected server-side (GitHub ruleset, no bypass actors).

```text
$ date -u
2026-11-21T00:04:38Z
$ git push origin HEAD:development
remote: error: GH013: Repository rule violations found for refs/heads/development.        
remote: - Changes must be made through a pull request.        
 ! [remote rejected] HEAD -> development (push declined due to repository rule violations)
error: failed to push some refs to 'https://github.com/victorgmrqs/chat-with-your-docs.git'
exit=1
$ git push origin HEAD:main
remote: error: GH013: Repository rule violations found for refs/heads/main.        
remote: - Changes must be made through a pull request.        
 ! [remote rejected] HEAD -> main (push declined due to repository rule violations)
error: failed to push some refs to 'https://github.com/victorgmrqs/chat-with-your-docs.git'
exit=1
$ git push origin --delete development
remote: error: GH013: Repository rule violations found for refs/heads/development.        
remote: - Cannot delete this branch        
 ! [remote rejected] development (push declined due to repository rule violations)
error: failed to push some refs to 'https://github.com/victorgmrqs/chat-with-your-docs.git'
$ gh api repos/victorgmrqs/chat-with-your-docs/rulesets/27773279
{"bypass_actors":[],"enforcement":"active","include":["refs/heads/main","refs/heads/development"],"name":"protect-main-and-development","rules":["deletion","non_fast_forward","pull_request"]}
$ gh api repos/victorgmrqs/chat-with-your-docs --jq .delete_branch_on_merge
true
```

## ai_foundation_rules_scoped

Two fresh headless sessions (`claude -p … --allowedTools Read`), each reading one temporary probe
file (`backend/app/probe.py`, `frontend/src/probe.tsx`, deleted afterwards) and reporting which
`.claude/rules/` headings were in context before and after the read.

```text
=== backend/app/probe.py
BEFORE: none / AFTER: # Backend architecture (ports and adapters)
=== frontend/src/probe.tsx
BEFORE: none / AFTER: # Frontend components
```

No rule is loaded at session start; each rule loads only for files matching its `paths`.

## ai_foundation_skill_curated

See `docs/skills-curation.md` and each `.claude/skills/*/SOURCE.md`. Mechanical sweep over the
vendored skills: no `allowed-tools`, no `!` auto-executed commands, no executable or non-Markdown
files, no zero-width/bidi characters, no broken internal links.

## docs-guard

```text
$ git add -N CHANGELOG.md && bash scripts/docs-guard.sh   # pre-commit: CHANGELOG.md is new, see known limitation
✅ docs-guard: ok
```

Known limitation: before the first commit, `docs-guard` reads `CHANGELOG.md` through `git diff`,
which shows nothing for an untracked file, so it reports a false failure. `git add -N` makes the
new file visible to `git diff`; once committed, the plain run passes.
