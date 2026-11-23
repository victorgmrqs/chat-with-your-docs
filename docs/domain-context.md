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
| DOM-11 | Retrieved chunks are delimited and escaped in the prompt, which states that they are data and never instructions. The context respects `CONTEXT_TOKEN_BUDGET` and the answer `ANSWER_MAX_TOKENS`. With `RERANK_ENABLED`, only reranked chunks reach the prompt and the sources; if the reranker fails or keeps no source id from its prompt, the fused order is used and the response says `reranked: false`. |
| DOM-12 | Technical failures (provider timeout, provider error, model refusal or content filter, invalid structured output after the adapter's retries) are reported as errors, `504 chat_timeout` or `502 chat_unavailable` (`502 retrieval_unavailable` when the question cannot be embedded), never as `insufficient_evidence`. Logs and span attributes carry diagnostic signals only (error type, provider, model, timings), never question, prompt, chunk or answer text (DOM-22). |
| DOM-13 | The chat provider and model come only from configuration (`CHAT_PROVIDER`, `CHAT_MODEL`). Every answer records the provider and model that produced it, in the response, in its content-free log line and on its trace. |

## Interface (CWYD-10, CWYD-5)

| ID | Rule |
|---|---|
| DOM-14 | One English screen, light theme only, Inter. Borders carry the hierarchy; there are no shadows. Colors, font sizes, line heights and radii come only from the tokens in `docs/design-tokens.json`, declared in `frontend/src/styles/theme.css`. |
| DOM-15 | Red (`destructive`, `status-failed`) is reserved for failures: a failed document, a failed upload, a request error. "Not enough evidence" is a normal outcome: it uses neutral colors, and its related passage is shown in a dashed box, never with a citation number. |
| DOM-16 | Copy about accepted files names the formats of DOM-01: a `.pdf` with selectable text, a `.md` or a `.txt`. This overrides the PDF-only copy in the design PNGs. Failure and rejection messages are the backend's own (DOM-01, DOM-03). |
| DOM-17 | The question input and Send are disabled while no document is `ready` and while an answer is loading; the hint says why. Asking while other documents are indexing is allowed, and a banner says only Ready documents are searched. |
| DOM-18 | A question that fails stays in the thread with the backend's message. Retry sends the same question again in place, and is offered only for failures that can pass on a second try: network errors and `5xx` (`chat_unavailable`, `retrieval_unavailable`, `chat_timeout`, `database_unavailable`). A `4xx` rejection (`empty_question`, `question_too_long`, `no_ready_documents`) shows its message without Retry. A document that failed with `indexing_failed` is retried by uploading the same file again: the file kept from this session, or the file picker after a reload. |
| DOM-19 | Document statuses and counters come only from the API. The list is loaded on start and fetched again every 2 s while any document is `indexing`; polling stops when none is, and a failed fetch does not stop it. An upload's response is shown at once; a list fetched before that upload is discarded and fetched again. Until the first fetch answers, the collection is unknown, not empty: the screen shows a loading state (or the load error), never "No documents yet" or counters. |

## Quality evaluation (CWYD-11)

| ID | Rule |
|---|---|
| DOM-20 | Every golden question in `backend/eval/dataset.yaml` names its expected outcome and, when answered, the sources that must support it: file name, page (PDF) or heading (Markdown), and a phrase the chunk must contain. A retrieved chunk matches an expected source only if all three agree. Retrieval hit@k is the share of expected sources matched within the top `RETRIEVAL_TOP_K` fused chunks. A citation is valid only if its chunk was retrieved for that question and matches one of the expected sources. |
| DOM-21 | A question the collection does not cover (out of scope or unrelated) is answered correctly only as `insufficient_evidence` with zero numbered sources; a sourced answer is a failed refusal. A technical failure (DOM-12) is recorded as an error for that question and never counts as a correct refusal; the run still reports every question. |

## Observability (CWYD-12)

| ID | Rule |
|---|---|
| DOM-22 | Question, prompt, chunk and answer text never go to span attributes. Only with `CAPTURE_CONTENT=true`, meant for development, they are added as span events. A failure is recorded on its span with error status and its exception type (`error.type`), never the exception message or stack trace, which can echo provider text. |
| DOM-23 | Every API response carries an `X-Request-ID` header made by the server (a client-supplied one is ignored), and every `{code, detail}` error body from the API carries the same `request_id` (the one exception: nginx rejects an oversized upload with `413 file_too_large` before it reaches the API, so that response has neither, and no trace); an unexpected failure answers `500 internal_error` with a generic message and that id. A question's trace carries it as `app.request_id`, so a user report leads to its trace. An ingestion runs after its upload request and is traced by `app.document.id`. |
| DOM-24 | Every chat model call that returns records its model and input/output tokens (a call that fails after the provider answered, e.g. invalid structured output, is recorded as an error without its tokens); a question records the totals and an estimated cost from the price table at `PRICE_TABLE_PATH` (USD per million tokens, matched by model-name prefix). A model without a price records no cost, never a wrong one. A question's trace ends with an outcome: `answered`, `refused` (`insufficient_evidence`) or `error`. |
