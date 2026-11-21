# Domain context

Business rules referenced in code as `# DOM-XX` at the point where they are enforced.
Change a rule here first, then the code.

## Ingestion (CWYD-3)

| ID | Rule |
|---|---|
| DOM-01 | Accepted formats: `.pdf` with selectable text, `.md` and `.txt`, up to `MAX_UPLOAD_MB` (default 10). The extension decides the format. Other types are rejected (`415 unsupported_type`), larger files with `413 file_too_large`, empty files with `400 empty_file`; each message tells the user what to upload instead. |
| DOM-02 | A document is `indexing` from upload until it ends as `ready` or `failed`. `ready` is written in the same transaction that stores its chunks, so a Ready document is always searchable. |
| DOM-03 | Failures have distinct reasons and messages. `no_extractable_text` is permanent (scanned or empty file: upload another version with selectable text). `indexing_failed` is transient (embeddings provider or storage unavailable after the adapter's own retries: upload the same file again). A document left `indexing` by a restart becomes `indexing_failed`. |
| DOM-04 | Uploads are idempotent per owner by SHA-256 of the file bytes: the existing document is returned and nothing is duplicated. Only a document that failed with `indexing_failed` is indexed again; `no_extractable_text` is returned as is. |
| DOM-05 | Every chunk keeps its provenance: document, file name, page (PDF, 1-based) or section heading path (Markdown, e.g. `Eligibility > Full-time employees`), its position and its original text. `chunk_id` is derived from document id and chunk index, so it is stable and unique across documents. The embedded text is prefixed with file name and page/section; the stored text is the original. |
| DOM-06 | Documents and chunks carry `owner_id`. The MVP has a single owner (`DEFAULT_OWNER_ID`) set by the application, never by the client or the LLM. |
