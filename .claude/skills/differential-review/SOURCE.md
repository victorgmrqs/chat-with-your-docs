# Source

- Upstream: https://github.com/trailofbits/skills
- Path: `plugins/differential-review`
- Commit: 149d7b21f4067765b82e67029730b42d228ef4b4
- License: CC BY-SA 4.0 (see `LICENSE`)
- Vendored: 2026-11-22 (CWYD-17)
- Modified: yes

## Attribution

"differential-review" skill by Omar Inuwa (Trail of Bits),
https://github.com/trailofbits/skills/tree/149d7b21f4067765b82e67029730b42d228ef4b4/plugins/differential-review,
licensed CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/).

This adapted copy is licensed CC BY-SA 4.0 too (ShareAlike), including every modified file in
this directory. Other licenses that apply to the rest of the repository do not cover it.

## Modifications

- `SKILL.md`:
  - Changed `allowed-tools` from `Read Write Grep Glob Bash` to Read, Grep, Glob and read-only
    git (`log`, `diff`, `blame`, `show`, `merge-base`, `rev-parse`).
  - Added `license` and `## Project overrides`; `description` scoped to security history and
    blast radius (general review is `/code-review-task`).
  - The report goes to the chat as input to `/code-review-task`: no report file and no
    APPROVE/REJECT verdict.
  - Removed the `adversarial-modeler` agent, the `audit-context-building` and `issue-writer`
    integrations, and the time estimates.
  - Rewrote the risk triggers and red flags for this stack.
- `methodology.md`:
  - Replaced `git checkout` with `git show <ref>:<path>`, and removed `gh pr view`.
  - Replaced the `audit-context-building` steps with manual tracing.
  - Replaced the Solidity globs and `grep` with Grep/Glob tool usage over the project's paths.
- `adversarial.md`: replaced the on-chain attacker types and the Solidity example with an
  HTTP/RAG attacker model and a citation-forging example.
- `patterns.md`:
  - Removed the Solidity/DeFi resources and patterns: double decrease, underflow, reentrancy,
    front-running, timestamp dependence, unchecked returns and gas DoS.
  - Kept regressions, missing validation and access control, rewritten with Python examples.
  - Added RAG and LLM patterns.
- `reporting.md`:
  - Reduced to a chat report: summary, changes, findings, coverage gaps, methodology.
  - Removed the emoji, the Solidity examples, the file locations (Desktop, `~/.claude`), the
    notification template and the issue-writer section.

## Dropped files

- `agents/adversarial-modeler.md`, `commands/diff-review.md`
- `skills/differential-review/agents/openai.yaml`, `skills/differential-review/assets/trail-of-bits-mark.svg`
- `README.md`, `.claude-plugin/plugin.json`
