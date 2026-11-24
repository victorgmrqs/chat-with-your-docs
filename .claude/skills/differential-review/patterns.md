<!-- Adapted from Trail of Bits' differential-review (CC BY-SA 4.0). See SOURCE.md. -->

# Common Vulnerability Patterns

Quick reference for detecting common security issues in code changes. For the project's own
conventions see `.claude/rules/security-*.md`.

---

## Security Regressions

**Pattern:** Previously removed code is re-added, or a fix is undone

**Detection:**
```bash
git log -S "pattern" --oneline --grep="security\|fix\|CVE"
```

**Red flags:**
- Commit message contains "security", "fix", "CVE", "vulnerability"
- Code removed <6 months ago
- No explanation in the current change for re-adding it

**Example:**
```python
# Removed in commit abc123 "fix: escape chunk text in the prompt"
# Re-added in the current change
return f"<source {attributes}>\n{chunk.text}\n</source>"  # REGRESSION: chunk can close the tag
```

---

## Missing Validation

**Pattern:** Removed check, limit or `raise` without replacement

**Detection:**
```bash
git diff "$BASE"..HEAD | grep -E "^-.*(raise |if not |max_|limit|assert )"
```

**Questions to ask:**
- Was validation moved elsewhere?
- Is it redundant (defensive programming)?
- Does removal expose a vulnerability?

**Example:**
```diff
- content = await file.read(settings.max_upload_bytes + 1)
+ content = await file.read()
```

**Risk:** An unbounded read buffers any body size in memory when the nginx limit is bypassed
(direct access to `:8000`).

---

## Access Control Bypass

**Pattern:** Removed or relaxed owner or status scoping

**Detection:**
```bash
git diff "$BASE"..HEAD | grep -E "^[-+].*(owner_id|status|Depends\()"
```

**Questions:**
- Who can now read or change this data?
- Does a value from the request body now decide the scope?
- Was the check moved to the caller?

**Example:**
```diff
- WHERE owner_id = :owner_id AND status = 'ready'
+ WHERE status = 'ready'
```

**Risk:** Questions retrieve chunks from every owner's documents.

---

## RAG and LLM Patterns

**Pattern:** Untrusted text crosses into instructions, logs or rendered output

**Detection:**
```bash
git diff "$BASE"..HEAD | grep -E "^\+.*(system=|SYSTEM_PROMPT|logger\.|set_attribute|innerHTML)"
```

**Questions:**
- Does chunk or question text reach the system prompt, a log line or a span attribute?
- Are citations still resolved only against labels sent in the prompt?
- Does model output reach the DOM as HTML, or a URL the browser fetches?
- Is every model call still bounded (input budget, `max_tokens`, timeout)?

---

## Quick Detection Commands

**Find removed checks:**
```bash
git diff "$BASE"..HEAD | grep "^-" | grep -E "raise |assert |if not "
```

**Find new external calls:**
```bash
git diff "$BASE"..HEAD | grep "^+" | grep -E "httpx|requests|ainvoke|invoke\(|fetch\("
```

**Find new SQL built from strings:**
```bash
git diff "$BASE"..HEAD | grep "^+" | grep -E "f\"(SELECT|INSERT|UPDATE|DELETE)|text\(f"
```

---

**For the analysis workflow, see [methodology.md](methodology.md)**
**For building exploit scenarios, see [adversarial.md](adversarial.md)**
