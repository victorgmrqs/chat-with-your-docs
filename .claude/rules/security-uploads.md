---
paths:
  - "backend/app/api/documents.py"
  - "backend/app/application/ingestion.py"
  - "backend/app/adapters/parsers.py"
  - "backend/app/adapters/postgres_documents.py"
  - "backend/app/domain/documents.py"
---

# Upload and parsing security

Uploaded files are untrusted input end to end: bytes, name and declared type.

- Size first: nginx caps the body (`security-nginx.md`), and the route reads at most
  `max_upload_bytes + 1` bytes so the use case can reject the rest (DOM-01). Never call
  `file.read()` without a limit or buffer a second copy of the content.
- The format comes from the extension (DOM-01), but the content must match it (target, CWYD-19):
  a `.pdf` starts with `%PDF-`; `.md`/`.txt` decode as strict UTF-8 (`utf-8-sig`, no
  `errors="ignore"` or `"replace"`). The client's `Content-Type` is never trusted for the
  decision.
- NUL characters never reach PostgreSQL (`_without_nul`); control characters in text are data,
  not markup.
- PDF parsing has a budget (target, CWYD-19): a maximum page count and a time limit, enforced
  outside the event loop (`asyncio.to_thread` plus a timeout). A parse that exceeds it fails as
  permanent `no_extractable_text`-style failure, never as a retryable one (DOM-03). Malformed
  PDFs raise many exception types: catch them at the adapter and map them to one domain error.
- PDFs are only read for text: never render, run JavaScript, follow links, open embedded files
  or decrypt with a guessed password.
- The stored name is display-only: sanitized and truncated (`MAX_FILENAME_LENGTH`), never used
  as a filesystem path or in a shell. Nothing is written to disk under a client-provided name;
  if files are ever stored, the key is server-generated (UUID).
- Deduplication is per owner by SHA-256 of the bytes (DOM-04); every query filters by
  `owner_id` set by the app (DOM-06), never by a value from the request body.
- Error responses follow `backend-api.md` (no exception text); logs carry document id, size,
  format and error type only, never file content or a path.
- Every new rejection path gets a test with a crafted file (wrong magic bytes, invalid UTF-8,
  oversized, page bomb) and a line in the endpoint's `docs/http/documents.http`.

Sources: OWASP File Upload Cheat Sheet; OWASP ASVS 5.0 V5 (File Handling); CWE-434, CWE-400,
CWE-22; pypdf security notes.
