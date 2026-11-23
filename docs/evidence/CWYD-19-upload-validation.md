# CWYD-19 — Upload content check and PDF parse budget

Evidence for the card's acceptance criteria (DOM-01, DOM-28). Outputs are verbatim; nothing is
mocked.

Environment: 2026-11-23, Docker 29.9.2, branch `feat/CWYD-19-upload-content-validation`. The API
image was built from the branch (`docker build backend`) and run with the database image on a
private Docker network, published on `127.0.0.1:18000`, plus a second API on `:18001` with
`PDF_PARSE_TIMEOUT_SECONDS=0.05`. Both use an invalid `OPENAI_API_KEY`: no real provider is
called, so a valid file stops at the embeddings step (`provider_misconfigured`), after the
content and page checks. A valid PDF reaching `ready` is covered by the integration tests
(`test_document_ingestion_pdf_at_the_page_limit_is_indexed`, real PostgreSQL, fake embeddings).

Inputs, generated in the scratchpad and never committed:

- `report.pdf`: PNG signature bytes renamed to `.pdf` (22 bytes).
- `notes.txt`: Latin-1 bytes `caf\xe9 latin-1`, not valid UTF-8.
- `huge.pdf`: 600 blank pages written with pypdf `PdfWriter` (74 515 bytes).
- `long.pdf`: the 2-page `expense-policy.pdf` fixture repeated to 300 pages (69 662 bytes).

Script: `curl -F file=@...` against each API, then `GET /documents/{id}` until the status leaves
`indexing` (fields filtered to filename, status, failure and `can_retry`). The `202` bodies of
the last two uploads were cut to 80 characters by the script; their polled result follows.

```text
### Renamed binary: PNG bytes saved as report.pdf
{"code":"unsupported_type","detail":"The file content does not match its .pdf extension. Upload a .pdf with selectable text, a .md or a .txt file.","request_id":"35414cf0-57e1-4f1b-a544-6b888cba589c"} [415]
### Invalid UTF-8 text (Latin-1 bytes) as notes.txt
{"code":"unsupported_type","detail":"The file content does not match its .txt extension. Upload a .pdf with selectable text, a .md or a .txt file.","request_id":"f25c60b5-928e-419b-9e40-084cc2e8ee63"} [415]
### List after both rejections (nothing stored)
[] [200]
### 600-page PDF (PDF_MAX_PAGES=500)
{"id":"a81c81ed-1735-4f10-8a13-91b1262bbd17","filename":"huge.pdf","format":"pdf","size_bytes":74515,"status":"indexing","failure_reason":null,"failure_message":null,"can_retry":false,"chunk_count":0,"created_at":"2026-11-23T13:52:17.975759Z","updated_at":"2026-11-23T13:52:17.975759Z"} [202]
{"filename": "huge.pdf", "status": "failed", "failure_reason": "too_many_pages", "failure_message": "The PDF has more pages than allowed. Split it into smaller files and upload those.", "can_retry": false}
### Same file again: permanent failure, returned as is
failed too_many_pages [200]
### Valid 2-page PDF: passes the content and page checks, reaches the embeddings step
{"id":"9110846a-8b2f-45f6-a14e-08482ad37da4","filename":"expense-policy.pdf","fo
{"filename": "expense-policy.pdf", "status": "failed", "failure_reason": "provider_misconfigured", "failure_message": "The embeddings provider rejected the configured API key or model. Ask the operator to check OPENAI_API_KEY and EMBEDDING_MODEL, then upload the same file again.", "can_retry": true}
### 300-page PDF on a second API with PDF_PARSE_TIMEOUT_SECONDS=0.05
{"id":"43192b96-5f40-4287-9c99-54c23a885293","filename":"long.pdf","format":"pdf
{"filename": "long.pdf", "status": "failed", "failure_reason": "parse_timeout", "failure_message": "Reading the PDF took too long. Save it again as a simpler PDF (for example with Print to PDF) or split it, then upload the new file.", "can_retry": false}
```

- A renamed binary and invalid UTF-8 text are rejected with `415 unsupported_type` before
  anything is stored (the list stays empty).
- 600 pages over the default limit of 500: `too_many_pages`, permanent (`can_retry: false`); the
  same file again answers `200` with the failed document (DOM-04).
- The valid PDF passes both checks and reaches the embeddings step.
- 300 pages under a 0.05 s budget: `parse_timeout`, permanent.

Tests (`uv run pytest`): backend unit and integration suites green, including
`test_check_content_*`, `test_parse_pdf_*_page_limit*`, `test_upload_content_not_matching_the_extension_raises`,
`test_index_pdf_over_the_page_limit_fails_permanently`, `test_index_pdf_parse_over_the_time_budget_fails_permanently`
(a stalled fake parser, no real wait), `test_ingestion_parse_timeout_ends_failed` (real PostgreSQL),
`test_document_ingestion_content_does_not_match_extension`, `test_document_ingestion_too_many_pages`
and `test_document_ingestion_client_filename_never_reaches_the_disk`.
