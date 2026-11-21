# CWYD-3 — Document ingestion smoke evidence

Evidence for the card's required scenarios against the real stack: real PostgreSQL + pgvector
and real OpenAI embeddings (`text-embedding-3-small`, 1536 dimensions). Outputs are verbatim;
response bodies are trimmed to the documented fields.

Environment: 2026-11-21, empty database (schema recreated with `alembic downgrade base` +
`upgrade head`), Docker 29.9.2, Docker Compose 5.6.1, branch
`feat/CWYD-3-document-ingestion`, stack started with `docker compose up --build --wait`. The
backend container runs `alembic upgrade head` before uvicorn. Requests were sent from the dev
container (`host.docker.internal` = the host's published ports) with the fixture documents in
`backend/tests/fixtures/documents`. The same requests are in `docs/http/documents.http`; the
automated equivalents are in `backend/tests/integration/test_documents_api.py`.

## indexing_failure and retry

First run with an invalid `OPENAI_API_KEY`: the provider answered `AuthenticationError`, the
adapter raised `EmbeddingUnavailable` and every text document ended `failed` with
`indexing_failed` ("Upload the same file again to retry"). The scanned PDF failed with
`no_extractable_text` without calling the provider. Backend log (error type only, no content):

```text
backend-1  | Indexing failed for document 574837e7-9a2a-4916-a383-2ae68f733fcd: EmbeddingUnavailable
```

After fixing the key and recreating the backend, the same files were uploaded again. Documents
that had failed with `indexing_failed` answered `202` with **the same id** and were indexed; the
scanned PDF, a permanent failure, answered `200` with the existing document and was not indexed
again (DOM-04). The same retry is covered by `test_document_ingestion_retry_after_indexing_failure`.

## document_ingestion_success, markdown_and_text, no_extractable_text, unsupported_type, duplicate_upload

```text
$ POST :8000/documents  file=expense-policy.pdf
202 {"id": "83d1cc58-9c66-4ec8-a03f-04f9cb245e68", "filename": "expense-policy.pdf", "status": "indexing", "chunk_count": 0, "failure_reason": null, "failure_message": null}
$ GET /documents/83d1cc58-9c66-4ec8-a03f-04f9cb245e68  (polled until terminal)
200 {"id": "83d1cc58-9c66-4ec8-a03f-04f9cb245e68", "filename": "expense-policy.pdf", "status": "ready", "chunk_count": 2, "failure_reason": null, "failure_message": null}
$ POST :8000/documents  file=remote-work-policy.pdf
202 {"id": "a9187372-7b36-4eb2-a3d7-9182ca19ce54", "filename": "remote-work-policy.pdf", "status": "indexing", "chunk_count": 0, "failure_reason": null, "failure_message": null}
$ GET /documents/a9187372-7b36-4eb2-a3d7-9182ca19ce54  (polled until terminal)
200 {"id": "a9187372-7b36-4eb2-a3d7-9182ca19ce54", "filename": "remote-work-policy.pdf", "status": "ready", "chunk_count": 2, "failure_reason": null, "failure_message": null}
$ POST :8000/documents  file=parental-leave-policy.md
202 {"id": "785d3537-154d-456e-9bd1-c2c5b23c9fda", "filename": "parental-leave-policy.md", "status": "indexing", "chunk_count": 0, "failure_reason": null, "failure_message": null}
$ GET /documents/785d3537-154d-456e-9bd1-c2c5b23c9fda  (polled until terminal)
200 {"id": "785d3537-154d-456e-9bd1-c2c5b23c9fda", "filename": "parental-leave-policy.md", "status": "ready", "chunk_count": 4, "failure_reason": null, "failure_message": null}
$ POST :8000/documents  file=office-handbook.txt
202 {"id": "fc8ad523-6929-46fe-9b6d-a0e31f058f89", "filename": "office-handbook.txt", "status": "indexing", "chunk_count": 0, "failure_reason": null, "failure_message": null}
$ GET /documents/fc8ad523-6929-46fe-9b6d-a0e31f058f89  (polled until terminal)
200 {"id": "fc8ad523-6929-46fe-9b6d-a0e31f058f89", "filename": "office-handbook.txt", "status": "ready", "chunk_count": 1, "failure_reason": null, "failure_message": null}
$ POST :8000/documents  file=scanned-notice.pdf
202 {"id": "d96ef901-e13a-4c67-8e64-1f1fbd9db990", "filename": "scanned-notice.pdf", "status": "indexing", "chunk_count": 0, "failure_reason": null, "failure_message": null}
$ GET /documents/d96ef901-e13a-4c67-8e64-1f1fbd9db990  (polled until terminal)
200 {"id": "d96ef901-e13a-4c67-8e64-1f1fbd9db990", "filename": "scanned-notice.pdf", "status": "failed", "chunk_count": 0, "failure_reason": "no_extractable_text", "failure_message": "No selectable text was found (for example a scanned PDF). Upload another version with selectable text."}
$ POST :8000/documents  file=unsupported.docx
415 {"code": "unsupported_type", "detail": ".docx is not supported. Upload a .pdf with selectable text, a .md or a .txt file."}
$ POST :8000/documents  file=empty.txt
400 {"code": "empty_file", "detail": "The file is empty. Upload a .pdf with selectable text, a .md or a .txt file."}
$ POST :8000/documents  file=expense-policy-copy.pdf
200 {"id": "83d1cc58-9c66-4ec8-a03f-04f9cb245e68", "filename": "expense-policy.pdf", "status": "ready", "chunk_count": 2, "failure_reason": null, "failure_message": null}
$ GET /documents/00000000-0000-0000-0000-0000000000ff
404 {"code": "document_not_found", "detail": "Document not found."}
$ POST :8080/api/documents  file=huge.txt
413 {"code": "file_too_large", "detail": "The file is too large. Upload a smaller file."}
$ GET /documents
  scanned-notice.pdf           failed  chunks=0   no_extractable_text
  office-handbook.txt          ready   chunks=1   None
  parental-leave-policy.md     ready   chunks=4   None
  remote-work-policy.pdf       ready   chunks=2   None
  expense-policy.pdf           ready   chunks=2   None
```

The 12 MB upload is rejected by the frontend's nginx (`client_max_body_size 11m`) with the same
`{code, detail}` envelope as the API.

## Chunk provenance and ownership (DOM-05, DOM-06)

PDF chunks keep their 1-based page, Markdown chunks their heading path, text files neither. Every
chunk carries its document's `owner_id`, a 1536-dimension embedding and a generated full-text
vector.

```text
$ docker compose exec db psql -U cwyd -d cwyd -c "SELECT d.filename, c.chunk_index, c.page,
    c.heading, c.owner_id = d.owner_id AS same_owner, vector_dims(c.embedding) AS dims,
    left(c.text, 48) AS text_start, c.search_vector IS NOT NULL AS fts FROM chunks c
    JOIN documents d ON d.id = c.document_id WHERE d.status = 'ready'
    ORDER BY d.filename, c.chunk_index"
         filename         | chunk_index | page |                          heading                          | same_owner | dims |             text_start             | fts 
--------------------------+-------------+------+-----------------------------------------------------------+------------+------+------------------------------------+-----
 expense-policy.pdf       |           0 |    1 |                                                           | t          | 1536 | Expense Policy                    +| t
                          |             |      |                                                           |            |      | 1. General rules                  +| 
                          |             |      |                                                           |            |      | Expenses must be                   | 
 expense-policy.pdf       |           1 |    2 |                                                           | t          | 1536 | 2. Coworking reimbursement        +| t
                          |             |      |                                                           |            |      | Coworking reimburseme              | 
 office-handbook.txt      |           0 |      |                                                           | t          | 1536 | Office Handbook                   +| t
                          |             |      |                                                           |            |      |                                   +| 
                          |             |      |                                                           |            |      | The office opens at 8 a.m. and     | 
 parental-leave-policy.md |           0 |      | Parental Leave Policy                                     | t          | 1536 | # Parental Leave Policy           +| t
                          |             |      |                                                           |            |      | This policy describes              | 
 parental-leave-policy.md |           1 |      | Parental Leave Policy > Eligibility > Full-time employees | t          | 1536 | ## Eligibility                    +| t
                          |             |      |                                                           |            |      | ### Full-time employees           +| 
                          |             |      |                                                           |            |      | Paren                              | 
 parental-leave-policy.md |           2 |      | Parental Leave Policy > Eligibility > Contractors         | t          | 1536 | ### Contractors                   +| t
                          |             |      |                                                           |            |      | Contractors are not covered by     | 
 parental-leave-policy.md |           3 |      | Parental Leave Policy > Duration                          | t          | 1536 | ## Duration                       +| t
                          |             |      |                                                           |            |      | Eligible employees receive sixteen | 
 remote-work-policy.pdf   |           0 |    1 |                                                           | t          | 1536 | Remote Work Policy                +| t
                          |             |      |                                                           |            |      | 1. Purpose                        +| 
                          |             |      |                                                           |            |      | This policy explai                 | 
 remote-work-policy.pdf   |           1 |    2 |                                                           | t          | 1536 | 2. Coworking spaces               +| t
                          |             |      |                                                           |            |      | Working from a coworking spa       | 
(9 rows)
```
