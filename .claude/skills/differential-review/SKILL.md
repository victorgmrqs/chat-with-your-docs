---
name: differential-review
description: "Performs security-focused differential review of code changes: classifies risk per file, uses git history to spot removed or re-added security code, counts callers for blast radius and checks test coverage of modified code. Use when reviewing a branch, commit or diff for security vulnerabilities, checking whether a change re-introduces a previously fixed bug, asking what else a change could break, or finding which modified code has no test covering it. For security history and blast radius; general review is /code-review-task."
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git log:*)
  - Bash(git diff:*)
  - Bash(git blame:*)
  - Bash(git show:*)
  - Bash(git merge-base:*)
  - Bash(git rev-parse:*)
license: CC-BY-SA-4.0
---

## Project overrides (Chat With Your Docs)

These project rules win over anything below (see `CLAUDE.md`, "Rules and skills").

- Read-only: use `git show <ref>:<path>` and `git diff`, never `git checkout`, `git stash` or
  anything that changes the working tree. No network (`gh`, `curl`).
- Default range: `$(git merge-base development HEAD)..HEAD`, plus uncommitted changes from
  `git diff HEAD`.
- Report as in `reporting.md`: in the chat, as input to `/code-review-task`; never a file and
  never an APPROVE/REJECT verdict.
- Check changes against `.claude/rules/security-*.md` and `docs/domain-context.md` (DOM-xx); a
  change that weakens a DOM rule is at least HIGH.
- The `CLAUDE.md` non-negotiables (no installs or one-off tools, no content or secrets in
  output) apply to findings too.

<!-- Adapted from Trail of Bits' differential-review (CC BY-SA 4.0). See SOURCE.md. -->

# Differential Security Review

Security-focused code review for branches, commits and diffs.

## Core Principles

1. **Risk-First**: Focus on trust boundaries, validation, data exposure, external calls
2. **Evidence-Based**: Every finding backed by git history, line numbers, attack scenarios
3. **Adaptive**: Scale to the size of the change (SMALL/MEDIUM/LARGE)
4. **Honest**: Explicitly state coverage limits and confidence level

---

## Rationalizations (Do Not Skip)

| Rationalization | Why It's Wrong | Required Action |
|-----------------|----------------|-----------------|
| "Small PR, quick review" | Heartbleed was 2 lines | Classify by RISK, not size |
| "I know this codebase" | Familiarity breeds blind spots | Build explicit baseline context |
| "Git history takes too long" | History reveals regressions | Never skip Phase 1 |
| "Blast radius is obvious" | You'll miss transitive callers | Calculate quantitatively |
| "No tests = not my problem" | Missing tests = elevated risk rating | Flag in report, elevate severity |
| "Just a refactor, no security impact" | Refactors break invariants | Analyze as HIGH until proven LOW |

---

## Quick Reference

### Change Size Strategy

| Size | Strategy | Approach |
|------|----------|----------|
| SMALL (<20 files) | DEEP | Read all deps, full git blame |
| MEDIUM (20-200) | FOCUSED | 1-hop deps, priority files |
| LARGE (200+) | SURGICAL | Critical paths only |

### Risk Level Triggers

| Risk Level | Triggers |
|------------|----------|
| HIGH | Auth/owner scoping, uploads and parsing, prompt building and citation resolution, external calls (LLM, embeddings), nginx headers and limits, validation removal |
| MEDIUM | Business logic, state changes, new public APIs, SQL |
| LOW | Comments, tests, UI copy, logging that carries no content |

---

## Workflow Overview

```
Pre-Analysis -> Phase 0: Triage -> Phase 1: Code Analysis -> Phase 2: Test Coverage
    -> Phase 3: Blast Radius -> Phase 4: Deep Context -> Phase 5: Adversarial -> Phase 6: Report
```

## Decision Tree

```
├─ Need detailed phase-by-phase methodology?
│  └─ Read: methodology.md (Pre-Analysis + Phases 0-4)
├─ Analyzing a HIGH RISK change?
│  └─ Read: adversarial.md (Phase 5: attacker model, exploit scenario, exploitability)
├─ Writing the report?
│  └─ Read: reporting.md (Phase 6: chat report structure)
├─ Looking for specific vulnerability patterns?
│  └─ Read: patterns.md (regressions, missing validation, access control, RAG)
└─ Quick triage only?
   └─ Use the Quick Reference above
```

---

## Quality Checklist

Before delivering:

- [ ] All changed files classified
- [ ] Git blame on removed security code
- [ ] Blast radius calculated for HIGH risk
- [ ] Attack scenarios are concrete (not generic)
- [ ] Findings reference specific line numbers + commits
- [ ] Coverage limits and confidence stated

---

## When NOT to Use This Skill

- **Documentation-only changes** (no security impact)
- **Formatting/linting** (cosmetic changes)
- **User explicitly requests quick summary only** (they accept risk)

## Red Flags (Stop and Investigate)

- Removed code from "security", "CVE" or "fix" commits
- `owner_id` filters, status filters or similarity floors removed or made request-controlled
- Validation removed without replacement
- External calls added without timeout or error mapping
- Prompt or chunk text reaching logs, span attributes or the system prompt
- High blast radius (50+ callers) + HIGH risk change

These patterns require adversarial analysis even in quick triage.
