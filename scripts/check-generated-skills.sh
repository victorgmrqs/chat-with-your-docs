#!/usr/bin/env bash
# check-generated-skills — the generated testing guides exist twice: the canonical output of
# /generate-test-guide in .dev-workflow/generated/skills/ and the copy Claude Code loads in
# .claude/skills/. Fails when any copy differs from its source (changed, missing or extra file).
# Runs in CI (job skills-drift) and locally from any directory of the repository.
set -euo pipefail
shopt -s nullglob

cd "$(git rev-parse --show-toplevel)"

SOURCE_DIR=".dev-workflow/generated/skills"
COPY_DIR=".claude/skills"

skills=("$SOURCE_DIR"/*/)
if [[ ${#skills[@]} -eq 0 ]]; then
  echo "❌ skills-drift: no generated skills under ${SOURCE_DIR}/ (wrong path?)"
  exit 1
fi

fail=0
for src in "${skills[@]}"; do
  name="$(basename "$src")"
  if ! diff -r "$src" "${COPY_DIR}/${name}"; then
    echo "❌ skills-drift: ${COPY_DIR}/${name} differs from ${SOURCE_DIR}/${name} (canonical)."
    echo "   Fix the canonical copy (or regenerate it), never the copy, then sync:"
    echo "   rm -rf ${COPY_DIR}/${name} && cp -r ${SOURCE_DIR}/${name} ${COPY_DIR}/${name}"
    fail=1
  fi
done

if [[ "$fail" -eq 0 ]]; then
  echo "✅ skills-drift: ${#skills[@]} generated skill(s) match their copies"
fi
exit "$fail"
