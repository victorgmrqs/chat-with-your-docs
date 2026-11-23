# CWYD-17 — Security skills and rules

Every rule glob matches tracked files, both skills parse with the intended frontmatter, and
the dangerous upstream instructions are gone from differential-review. Generated on 2026-11-22
on branch `feat/CWYD-17-security-skills-rules` by a Python script over `git ls-files` and the
files themselves; output verbatim.

```text
### Rule globs -> tracked files
security-nginx.md (38 lines)
  frontend/nginx/**                             1 match(es): frontend/nginx/default.conf.template
security-uploads.md (40 lines)
  backend/app/api/documents.py                  1 match(es): backend/app/api/documents.py
  backend/app/application/ingestion.py          1 match(es): backend/app/application/ingestion.py
  backend/app/adapters/parsers.py               1 match(es): backend/app/adapters/parsers.py
  backend/app/adapters/postgres_documents.py    1 match(es): backend/app/adapters/postgres_documents.py
  backend/app/domain/documents.py               1 match(es): backend/app/domain/documents.py
security-llm.md (43 lines)
  backend/app/application/answering.py          1 match(es): backend/app/application/answering.py
  backend/app/application/prompts.py            1 match(es): backend/app/application/prompts.py
  backend/app/adapters/*_chat.py                3 match(es): backend/app/adapters/anthropic_chat.py, backend/app/adapters/langchain_chat.py, backend/app/adapters/openai_chat.py
  backend/app/adapters/postgres_retriever.py    1 match(es): backend/app/adapters/postgres_retriever.py
  backend/app/domain/answers.py                 1 match(es): backend/app/domain/answers.py
  backend/eval/dataset.yaml                     1 match(es): backend/eval/dataset.yaml
  frontend/src/components/AnswerCard.tsx        1 match(es): frontend/src/components/AnswerCard.tsx

### Skills frontmatter
owasp-security: name=owasp-security license=MIT allowed-tools=(none)
  owasp-security/LICENSE (21 lines)
  owasp-security/SKILL.md (154 lines)
  owasp-security/SOURCE.md (29 lines)
  owasp-security/reference/config-and-supply-chain.md (245 lines)
  owasp-security/reference/languages.md (103 lines)
  owasp-security/reference/review-checklist.md (134 lines)
  owasp-security/reference/standards.md (72 lines)
differential-review: name=differential-review license=CC-BY-SA-4.0 allowed-tools=['Read', 'Grep', 'Glob', 'Bash(git log:*)', 'Bash(git diff:*)', 'Bash(git blame:*)', 'Bash(git show:*)', 'Bash(git merge-base:*)', 'Bash(git rev-parse:*)']
  differential-review/LICENSE (427 lines)
  differential-review/SKILL.md (132 lines)
  differential-review/SOURCE.md (51 lines)
  differential-review/adversarial.md (170 lines)
  differential-review/methodology.md (172 lines)
  differential-review/patterns.md (119 lines)
  differential-review/reporting.md (86 lines)

### Hidden or non-ASCII characters in new/changed text (excluding LICENSE)
  .claude/skills/owasp-security/reference/standards.md:31 U+2248
  unexpected characters: 1

### Forbidden instructions left in differential-review
  git checkout             outside SOURCE.md: ['.claude/skills/differential-review/SKILL.md']
  gh pr                    outside SOURCE.md: none
  audit-context-building   outside SOURCE.md: none
  issue-writer             outside SOURCE.md: none
  Desktop                  outside SOURCE.md: none
  adversarial-modeler      outside SOURCE.md: none
  APPROVE/REJECT           outside SOURCE.md: ['.claude/skills/differential-review/reporting.md', '.claude/skills/differential-review/SKILL.md']
```

The one non-ASCII character is `≈` in upstream text, now in `reference/standards.md` (`≈70% cumulative` in the ASVS level table), not a
hidden character.

The remaining "forbidden" matches are the prohibitions themselves (Project overrides and the
no-verdict note in `reporting.md`).
