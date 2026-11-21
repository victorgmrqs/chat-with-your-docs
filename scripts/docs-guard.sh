#!/usr/bin/env bash
# docs-guard — every task needs a CHANGELOG entry linked to its card; code needs tests.
# Installed by /setup-project; runs in CI and in /code-review-task.
# Complements (does not replace) the semantic check of the skill.
set -euo pipefail

BASE_BRANCH="${BASE_BRANCH:-development}"
SRC_PATTERN="${SRC_PATTERN:-^(backend/app/|frontend/src/)}"   # production code
TEST_PATTERN="${TEST_PATTERN:-(\.test\.|\.spec\.|/tests?/|^(backend|frontend)/(tests?|e2e)/|(^|/)test_[^/]*\.py$)}"
CHANGELOG="${CHANGELOG:-CHANGELOG.md}"

base_ref="${BASE_BRANCH}"
if git rev-parse --verify "origin/${BASE_BRANCH}" >/dev/null 2>&1; then
  base_ref="origin/${BASE_BRANCH}"
fi
files="$({
  git diff --name-only "${base_ref}"...HEAD
  git diff --name-only
  git ls-files --others --exclude-standard
} | sort -u)"

src_changed="$(echo "$files" | grep -E "$SRC_PATTERN" | grep -vE "$TEST_PATTERN" || true)"
task_changed="$(echo "$files" | grep -v '^task-brief\.yaml$' | sed '/^$/d' || true)"
fail=0

if [[ -n "$task_changed" ]]; then
  if ! echo "$files" | grep -qx "$CHANGELOG"; then
    echo "❌ docs-guard: every task must update ${CHANGELOG} [Unreleased]."
    fail=1
  fi

  ticket_id="${TICKET_ID:-}"
  if [[ -z "$ticket_id" ]]; then
    branch_name="$(git branch --show-current)"
    ticket_id="$(echo "$branch_name" | grep -Eo '[A-Z][A-Z0-9]+-[0-9]+' | head -n 1 || true)"
  fi

  if [[ -z "$ticket_id" ]]; then
    echo "❌ docs-guard: set TICKET_ID or put the card ID in the branch name."
    fail=1
  elif echo "$files" | grep -qx "$CHANGELOG"; then
    changelog_diff="$({
      git diff "${base_ref}"...HEAD -- "$CHANGELOG"
      git diff -- "$CHANGELOG"
    } 2>/dev/null || true)"
    if ! echo "$changelog_diff" | grep -E "^\+.*\[${ticket_id}\]\(https?://[^)]*/browse/${ticket_id}\)" >/dev/null; then
      echo "❌ docs-guard: ${CHANGELOG} must contain a Markdown link to card ${ticket_id}."
      fail=1
    fi
  fi
fi

if [[ -n "$src_changed" ]]; then
  if ! echo "$files" | grep -qE "$TEST_PATTERN"; then
    echo "❌ docs-guard: production code changed without any test in the diff."
    fail=1
  fi
fi

if [[ "$fail" -eq 0 ]]; then
  echo "✅ docs-guard: ok"
fi
exit "$fail"
