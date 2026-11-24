#!/usr/bin/env bash
# dev-workflow: opens the sprint loop session (/loop /sprint) in the dedicated clone.
# From the plugin's templates/loop/ (dev-workflow 0.8.0), translated. Guide: the plugin's docs/sprint-loop.md.
# Usage: scripts/loop/start.sh [--model opus] [--check]
#   --check only checks the environment, without opening the session.
# To stop: create the loop.stop_file (default .loop-stop) at the clone root.
set -euo pipefail

model=opus
check=0
while [ $# -gt 0 ]; do
  case "$1" in
    --model) model=$2; shift 2 ;;
    --check) check=1; shift ;;
    *) echo "usage: $0 [--model <model>] [--check]" >&2; exit 2 ;;
  esac
done

fail() { echo "error: $*" >&2; exit 1; }

root=$(git rev-parse --show-toplevel) || fail "not a git repository"
cd "$root"

config=.dev-workflow/workflow.config.yaml
[ -f "$config" ] || fail "missing $config"
loop_block=$(sed -n '/^loop:/,/^[^[:space:]#]/p' "$config")
echo "$loop_block" | grep -Eq '^[[:space:]]+enabled:[[:space:]]*true' || fail "loop.enabled is not true in $config"
echo "$loop_block" | grep -Eq '^[[:space:]]+required_check:[[:space:]]*"?[A-Za-z0-9]' || fail "loop.required_check is empty in $config"
stop_file=$(echo "$loop_block" | sed -n 's/^[[:space:]]*stop_file:[[:space:]]*\([^[:space:]#]*\).*/\1/p')
stop_file=${stop_file:-.loop-stop}
[ -e "$stop_file" ] && fail "$stop_file exists at the root; delete it to start the loop"

# Full clone, not a worktree: in a worktree .git is a file and local hooks may not run.
[ -d .git ] || fail "run in a full clone dedicated to the loop, not in a worktree"
[ -f scripts/loop/settings.json ] || fail "missing scripts/loop/settings.json (copy it from the plugin's templates/loop/)"

[ -n "$(git config user.email || true)" ] || fail "git config user.email is empty: commits would hang with nobody to answer"
gh auth status >/dev/null 2>&1 || fail "gh is not logged in: run gh auth login"
command -v claude >/dev/null 2>&1 || fail "claude not found in PATH"

# Local changes may be the task the loop left in progress: /sprint decides to resume or stop.
dirty=$(git status --porcelain)
[ -n "$dirty" ] && printf 'warning: working tree has changes. This clone must belong to the loop only:\n%s\n' "$dirty" >&2

echo "Environment ok: $root ($(git branch --show-current))"
[ "$check" = 1 ] && exit 0

echo 'Keep the machine awake while the loop runs.'
export DEV_WORKFLOW_LOOP=1
exec claude --permission-mode auto --settings scripts/loop/settings.json --model "$model" '/loop /sprint'
