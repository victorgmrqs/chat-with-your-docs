<!-- Adapted from Trail of Bits' differential-review (CC BY-SA 4.0). See SOURCE.md. -->

# Differential Review Methodology

Detailed phase-by-phase workflow for security-focused code review.

## Pre-Analysis: Baseline Context Building

Build an understanding of the baseline before judging the change. Read baseline versions with
`git show`, never by checking them out:

```bash
BASE=$(git merge-base development HEAD)
git show "$BASE":backend/app/application/answering.py   # baseline version of a file
```

**Capture from the baseline:**
- System-wide invariants (what must ALWAYS be true): `docs/domain-context.md` (DOM-xx) and
  `CLAUDE.md` "Non-negotiable constraints" state most of them
- Trust boundaries (HTTP request, uploaded file, retrieved chunk, model output, provider error)
- Validation patterns (what gets checked where - defense-in-depth)
- Call graphs for critical functions (who calls what)
- External dependencies and trust assumptions

**Why this matters:**
- Understand what the code was SUPPOSED to do before changes
- Detect when changes violate baseline invariants or break defense-in-depth

---

## Phase 0: Intake & Triage

**Extract changes:**
```bash
git diff "$BASE"..HEAD --stat
git log "$BASE"..HEAD --oneline
git diff "$BASE"..HEAD --name-only
git diff HEAD --stat          # uncommitted work, if any
```

**Assess size:** count changed files from `--name-only`; count project source files with the
Glob tool (`backend/app/**/*.py`, `frontend/src/**/*.{ts,tsx}`).

**Classify complexity:**
- **SMALL**: <20 files → Deep analysis (read all deps)
- **MEDIUM**: 20-200 files → Focused analysis (1-hop deps)
- **LARGE**: 200+ files → Surgical (critical paths only)

**Risk score each file** with the triggers in `SKILL.md`.

---

## Phase 1: Changed Code Analysis

For each changed file:

1. **Read both versions** (`git show "$BASE":<path>` and the working tree)

2. **Analyze each diff region:**
   ```
   BEFORE: [exact code]
   AFTER: [exact code]
   CHANGE: [behavioral impact]
   SECURITY: [implications]
   ```

3. **Git blame removed code:**
   ```bash
   # When was it added? Why?
   git log -S "removed_code" --oneline
   git blame "$BASE" -- backend/app/domain/answers.py
   ```

   **Red flags:**
   - Removed code from "fix", "security", "CVE" commits → CRITICAL
   - Recently added (<1 month) then removed → HIGH

4. **Check for regressions (re-added code):**
   ```bash
   git log -S "added_code" -p
   ```

   Pattern: Code added → removed for security → re-added now = REGRESSION

5. **Micro-adversarial analysis** for each change:
   - What attack did removed code prevent?
   - What new surface does new code expose?
   - Can modified logic be bypassed?
   - Are checks weaker? Edge cases covered?

6. **Generate concrete attack scenarios:**
   ```
   SCENARIO: [attack goal]
   PRECONDITIONS: [required state]
   STEPS:
     1. [specific action]
     2. [expected outcome]
     3. [exploitation]
   WHY IT WORKS: [reference code change]
   IMPACT: [severity + scope]
   ```

---

## Phase 2: Test Coverage Analysis

```bash
git diff "$BASE"..HEAD --name-only -- backend/app frontend/src   # production code
git diff "$BASE"..HEAD --name-only -- backend/tests frontend/src/**/*.test.*
```

For each changed function, search for tests with the Grep tool (pattern: the function name;
paths: `backend/tests/`, `frontend/src/`, `frontend/e2e/`).

**Risk elevation rules:**
- NEW function + NO tests → Elevate risk MEDIUM→HIGH
- MODIFIED validation + UNCHANGED tests → HIGH RISK
- Complex logic (>20 lines) + NO tests → HIGH RISK

---

## Phase 3: Blast Radius Analysis

Count callers of each modified function with the Grep tool (pattern `functionName\(`, output
mode `count`, over `backend/` or `frontend/src/`).

**Classify blast radius:**
- 1-5 calls: LOW
- 6-20 calls: MEDIUM
- 21-50 calls: HIGH
- 50+ calls: CRITICAL

**Priority matrix:**

| Change Risk | Blast Radius | Priority | Analysis Depth |
|-------------|--------------|----------|----------------|
| HIGH | CRITICAL | P0 | Deep + all deps |
| HIGH | HIGH/MEDIUM | P1 | Deep |
| HIGH | LOW | P2 | Standard |
| MEDIUM | CRITICAL/HIGH | P1 | Standard + callers |

---

## Phase 4: Deep Context Analysis

For each HIGH RISK changed function, trace by reading code (Read, Grep):

1. **Map the function flow:** entry conditions (validation, dependencies, owner scoping), state
   reads and writes (tables, columns), external calls (LLM, embeddings, database), return values
   and side effects (background tasks, logs, spans).
2. **Trace internal calls:** list the functions called and build the call graph.
3. **Trace external calls:** trust boundaries crossed, assumptions about provider behavior
   (timeouts, error bodies, refusals).
4. **Identify invariants:** what must ALWAYS be true, what must NEVER happen, and whether they
   still hold after the change.
5. **Five Whys root cause:** why was this code changed, why did the original exist, why might
   this break, why this approach, why could this fail in production.

**Cross-cutting pattern detection:** search the codebase for the defensive pattern the change
touches and check if any instance was removed:

```bash
git diff "$BASE"..HEAD | grep -E "^-.*(owner_id|status ==|escape\(|max_upload_bytes|raise )"
```

**Flag if removal breaks defense-in-depth.**

---

**Next steps:**
- For HIGH RISK changes, proceed to [adversarial.md](adversarial.md)
- For the report, see [reporting.md](reporting.md)
