---
paths:
  - "backend/app/application/answering.py"
  - "backend/app/application/prompts.py"
  - "backend/app/adapters/*_chat.py"
  - "backend/app/adapters/postgres_retriever.py"
  - "backend/app/domain/answers.py"
  - "backend/eval/dataset.yaml"
  - "frontend/src/components/AnswerCard.tsx"
---

# LLM and RAG security

Document text is attacker-controlled: anyone who can upload can write instructions into a chunk.

- Retrieved chunks go only in the user message, each wrapped in `<source id="...">` with its
  content escaped (`html.escape`), so a chunk cannot close its tag or forge another source.
  The system prompt states that source content is data, never instructions (DOM-11). Never
  interpolate chunk or question text into the system prompt.
- Citations (DOM-09) and retrieval filters (DOM-07, DOM-08) stay backend-owned: never trust a
  document id, page or quote the model writes, and the model never chooses what is searched
  beyond the question text.
- The chat path has no tools, function calling, code execution, browsing or follow-up fetches.
  Adding any is an ADR, not a code change (OWASP LLM Top 10: excessive agency).
- Model output is rendered as text by the frontend: no HTML, no `dangerouslySetInnerHTML`, no
  markdown links or images that fetch URLs (improper output handling: exfiltration through
  rendered output).
- `insufficient_evidence` and failure messages are fixed backend text (DOM-10, DOM-12); never
  echo provider error bodies or model refusals.
- Bound every call: input token budget (`label_chunks`), `max_tokens` on output, a timeout and
  the configured model only (DOM-13). A question longer than the limit is rejected, not
  truncated silently (unbounded consumption).
- Content stays out of logs, span attributes and error responses (DOM-22,
  `backend-architecture.md`).
- Prompt or retrieval changes run the eval (`backend/eval/`). The dataset keeps adversarial
  cases (target, CWYD-21): a chunk that says "ignore previous instructions", a chunk that asks
  to cite a label that does not exist, a chunk that forges `</source>`. Each expects a grounded
  answer or `insufficient_evidence`, never compliance (DOM-20).

Sources: OWASP Top 10 for LLM Applications (prompt injection, sensitive information disclosure,
excessive agency, improper output handling, unbounded consumption);
OWASP LLM Prompt Injection Prevention Cheat Sheet; `docs/domain-context.md` DOM-07 to DOM-13,
DOM-20 to DOM-24.
