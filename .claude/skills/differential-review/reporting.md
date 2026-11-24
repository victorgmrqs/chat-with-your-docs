<!-- Adapted from Trail of Bits' differential-review (CC BY-SA 4.0). See SOURCE.md. -->

# Report (Phase 6)

The report goes to the chat, as input to `/code-review-task`. No file is written and no
APPROVE/REJECT verdict is given: the gate decides.

---

## Report Structure

### 1. Summary

```markdown
## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | X |
| HIGH | Y |
| MEDIUM | Z |
| LOW | W |

**Overall risk:** CRITICAL/HIGH/MEDIUM/LOW
**Blocking candidates for the gate:** [finding titles, or "none"]

- Files analyzed: X/Y
- Test coverage gaps: N functions
- High blast radius changes: M functions
- Security regressions detected: P
```

### 2. What Changed

```markdown
**Range:** `base..head` (X commits)

| File | +Lines | -Lines | Risk | Blast Radius |
|------|--------|--------|------|--------------|
| backend/app/api/documents.py | +50 | -20 | HIGH | MEDIUM |
```

### 3. Findings

For each finding, most severe first:

```markdown
### [SEVERITY] Title

**File**: path/to/file.py:L123 (commit abc123)
**Blast Radius**: N callers
**Test Coverage**: YES/NO/PARTIAL
**Rule**: DOM-xx or `.claude/rules/security-*.md` item, if one applies

**Description**: [clear explanation]
**Historical Context**: [git blame: when and why the code existed]
**Attack Scenario**: [concrete steps, from adversarial.md]
**Recommendation**: [specific fix]
```

### 4. Test Coverage Gaps

```markdown
| Function | Risk | Missing scenario |
|----------|------|------------------|
| upload() | HIGH | invalid UTF-8 `.txt` |
```

### 5. Methodology and Limits

```markdown
**Strategy:** DEEP/FOCUSED/SURGICAL
**Scope:** files reviewed, HIGH RISK coverage
**Techniques:** git blame on removals, blast radius, coverage, adversarial modeling
**Limitations:** [what was not analyzed]
**Confidence:** HIGH/MEDIUM/LOW
```

---

## Formatting Guidelines

- Markdown tables for structured data; code blocks with the language (`python`, `ts`, `nginx`)
- Severity as words (CRITICAL, HIGH, MEDIUM, LOW), no emoji
- Line references as `path/to/file.py:L123`, with the commit when it matters
- Before/after comparisons as a `diff` block
