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

## Answering (CWYD-4)

| ID | Rule |
|---|---|
| DOM-07 | A question searches only the `ready` documents of the request owner. Owner and status filters are set by the application, never by the client or the LLM. Control characters (other than tab and newline) are removed from the question. A question with no Ready document is rejected with `409 no_ready_documents`; an empty question with `400 empty_question`, one longer than `QUESTION_MAX_CHARS` with `400 question_too_long`. |
| DOM-08 | A retrieved chunk counts as evidence only if its cosine similarity is at least `MIN_RELEVANCE` or it matched the full-text search. With no evidence the chat model is not called and the outcome is `insufficient_evidence`. |
| DOM-09 | The model cites the context labels it was given. The backend keeps only labels that were in the prompt and drops invented ones with their markers, as well as any numeric marker the model wrote itself (e.g. a `[3]` copied from a footnote); the kept citations are renumbered `1..n` by first appearance and each source is built from the stored chunk (file name, page or heading, passage). An answer left without any valid citation becomes `insufficient_evidence`. |
| DOM-10 | `insufficient_evidence` carries a fixed message written by the backend, never model text. The closest passage may be returned separately as `related_passage`, without a citation number. "Not enough evidence" is a normal outcome, not an error. |
| DOM-11 | Retrieved chunks are delimited and escaped in the prompt, which states that they are data and never instructions. The context respects `CONTEXT_TOKEN_BUDGET` and the answer `ANSWER_MAX_TOKENS`. With `RERANK_ENABLED`, only reranked chunks reach the prompt and the sources; if the reranker fails, the fused order is used and the response says `reranked: false`. |
| DOM-12 | Technical failures (provider timeout, provider error, model refusal or content filter, invalid structured output after the adapter's retries) are reported as errors, `504 chat_timeout` or `502 chat_unavailable` (`502 retrieval_unavailable` when the question cannot be embedded), never as `insufficient_evidence`. Logs carry diagnostic signals only (error type, provider, model, timings), never question, prompt, chunk or answer text. |
| DOM-13 | The chat provider and model come only from configuration (`CHAT_PROVIDER`, `CHAT_MODEL`). Every answer records the provider and model that produced it, in the response and in its content-free log line. |
