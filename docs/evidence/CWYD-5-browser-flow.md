# CWYD-5 — Upload, status and chat against the API

Card: [CWYD-5](https://goncalvesmarques.atlassian.net/browse/CWYD-5). The screen runs against the
real API through the Compose stack (Part A) and, for failures the real backend cannot produce on
demand, against the MSW mock in the browser (Part B). Files come from
`backend/tests/fixtures/documents/`, plus an empty `empty.txt` and `benefits-flaky.txt` (mock
trigger). QA run on 2026-11-22 in Chrome, driven by an agent and checked by a human; screenshots
in [`CWYD-5/`](CWYD-5/).

```bash
docker compose down -v && docker compose up --build --wait   # web http://localhost:8080
cd frontend && VITE_API_MOCKS=true npm run dev               # Part B, no backend needed
```

## Part A — real stack

| ID | Step | Expected | Rules | Result | Screenshot |
|---|---|---|---|---|---|
| A1 | Open with an empty collection | "No documents yet", onboarding; input and Send disabled with the reason | DOM-17 | PASS | [1-empty](CWYD-5/1-empty.png) |
| A2 | Upload `remote-work-policy.pdf` + `expense-policy.pdf` | Both rows **Indexing** at once; counters "0 ready · 2 indexing"; indexing banner | DOM-02, DOM-19 | PASS (retest): rows Indexing within 0.4 s, banner and disabled input with "2 documents are still indexing" | — (state lasted ~5 s) |
| A3 | Wait without reloading | Rows turn **Ready** by themselves; polling stops | DOM-19 | PASS (retest): Ready ~5 s after upload, "2 ready", input enabled, banner gone | — |
| A4 | Ask "Can I work from a coworking space, and what is the monthly reimbursement limit?" | Loading card with input disabled; answer with citation chips; Sources (2) with file, page and passage; both documents highlighted | DOM-09, DOM-17 | PASS | [3-answer](CWYD-5/3-answer.png) |
| A5 | Click a citation chip | Scrolls to its source card | — | PASS | — |
| A6 | Upload `parental-leave-policy.md`; ask about contractors | Source shows a section path; only that document highlighted; earlier answer compact | DOM-05 | PASS | [4-answer-section](CWYD-5/4-answer-section.png) |
| A7 | Ask "Can parental leave be split into several separate periods?" | Neutral "Not enough evidence", no numbered citation, related passage, no highlight | DOM-10, DOM-15 | PASS | [5-not-enough-evidence](CWYD-5/5-not-enough-evidence.png) |
| A8 | "Rephrase the question" | Question back in the input | — | PASS | — |
| A9 | Shift+Enter | New line, nothing sent | — | PASS | — |
| A10 | Upload `unsupported.docx` | Red "wasn't added" with the backend message; no row | DOM-01, DOM-16 | PASS | [6-rejection](CWYD-5/6-rejection.png) |
| A11 | Upload `empty.txt` | Red "wasn't added", "The file is empty. …" | DOM-01 | PASS | — |
| A12 | Upload `scanned-notice.pdf` | **Failed** with the no-text message, "Upload another file", no Retry | DOM-03 | PASS | [7-failed-document](CWYD-5/7-failed-document.png) |
| A13 | Stop the backend, ask | Red error card, question kept, **Retry** | DOM-12, DOM-18 | PASS | [8-request-failure](CWYD-5/8-request-failure.png) |
| A14 | Start the backend, Retry | Answered in place, question shown once | DOM-18 | PASS | [9-retry-answered](CWYD-5/9-retry-answered.png) |
| A15 | Stop the backend, reload | Loading state, then "Couldn't load your documents" with a compact Retry; sidebar "Your documents couldn't be loaded."; no empty state, no counters | DOM-19 | PASS (retest, after the fix below) | [10-load-failure](CWYD-5/10-load-failure.png) (first run, before the fix) |
| A16 | Start the backend, Retry | Alert gone, list back | DOM-19 | PASS (retest) | — |

## Part B — mock mode

| ID | Step | Expected | Result | Screenshot |
|---|---|---|---|---|
| B1 | Upload `benefits-flaky.txt` | Indexing → **Failed** (temporary) with **Retry** | PASS | [11-indexing-failed](CWYD-5/11-indexing-failed.png) |
| B2 | Retry | Sent again without a file dialog; Indexing → Ready | PASS | — |
| B3 | Ask "timeout test" | Red "The answer took too long…" with Retry | PASS | — |
| B4 | Retry | Answered in place | FAIL in the first run (the mock timed out on every attempt) → fixed → PASS (retest) | — |
| B5 | Ask "unknown topic" | Neutral "Not enough evidence" with a related passage | PASS | — |
| B6 | Reload after a failed upload | Session files are gone; state resets | PASS | — |

## Findings fixed after the run

- **The sidebar scrolled away with a long conversation** ([before](CWYD-5/0-before-sidebar-scrolls-away.png)):
  the whole page scrolled, so the upload button left the screen. From `md` up the screen is now
  an app shell: the sidebar stays fixed, only the conversation scrolls (to the latest turn on send
  and on answer) and the question input stays at the bottom.
- **A not-yet-loaded list looked empty** (A15 anomaly): while the first `GET /documents` was
  pending, the screen showed "No documents yet" and "0 ready"; under a load error, the
  empty-collection onboarding as well. Now a loading state is shown until the first answer, and a
  failed load shows only the error (DOM-19).
- **Blank main column when every document failed**: the upload invitation is shown whenever
  nothing is Ready or Indexing and nothing was asked.
- **Low-contrast focus ring** (50% opacity): one solid 2px outline with a 2px offset for every
  focusable element, citation links and scroll areas included.
- **Full-width Retry** in the load-error alert: now compact, like the answer-error card.
- **Mock data**: "Page 1" on a `.txt` source; the mock now gives pages to PDFs, sections to
  Markdown and no location to plain text (DOM-05).

Retest after the fixes (rebuilt stack, empty collection): A2, A3, A15, A16, B1–B4 and a keyboard pass
(solid outline on the textarea, Send and Upload; visible on white and on the blue Send) all PASS.
Screenshots 3, 4, 5 and 10 are from the first run, before the fixes: 3–5 show the old page
scroll (content and states unchanged), 10 shows the empty state under the error that is now gone.
A focusable scroll area clipped its own outline at the viewport edge; scroll areas now draw it
inside.

## Automated coverage

`npm --prefix frontend test` runs the card's scenarios against MSW handlers typed from the
OpenAPI schema (`src/App.test.tsx`, `src/hooks/useDocuments.test.ts`,
`src/components/ChatThread.test.tsx`):

| Scenario | Test |
|---|---|
| `docs_chat_success` | uploads two documents, waits for Ready via polling, asks, checks file, page or section and passage of both sources and the sidebar highlight |
| `docs_chat_no_ready_documents` | input and Send disabled with the hint while the only document is indexing |
| `docs_chat_insufficient_evidence` | neutral card, related passage, no numbered citation, no highlight |
| `docs_chat_request_failure` | 504 keeps the question and retries in place; 409 shows the message without Retry; network failure is retryable |
| Polling (DOM-19) | polls while indexing, stops when none is, survives a failed fetch; a list older than an upload is fetched again; no empty state while loading or after a failed load |
| Uploads | `.docx` rejection message; `indexing_failed` retried with the same file |
| Layout | scrolls to the latest turn on send and on answer, not on mount; upload invitation when every document failed |
