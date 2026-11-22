# RAG evaluation — `baseline`

Application defaults — hybrid retrieval (vector + full-text, RRF), reranker off, chunks of 1000/150 characters, MIN_RELEVANCE 0.30.

- Run: 2026-11-22 22:16 UTC
- Dataset: `backend/eval/dataset.yaml` (sha256 `18cf4aa7427b`)
- Settings: `chat_provider=anthropic`, `chat_model=claude-haiku-5-5`, `embedding_model=text-embedding-3-small`, `chunk_size=1000`, `chunk_overlap=150`, `retrieval_candidates=20`, `retrieval_top_k=6`, `min_relevance=0.3`, `rerank_enabled=False`, `rerank_top_n=4`, `context_token_budget=3000`, `answer_max_tokens=800`, `chat_temperature=None`

## Summary

| Metric | Value |
|---|---|
| Questions (errors) | 13 (0) |
| Outcome accuracy | 100% |
| Retrieval hit@k (mean) | 100% |
| Expected-source MRR | 0.93 |
| Correct refusal rate | 100% |
| Citation validity | 100% |
| Citation recall (mean) | 100% |
| Latency p50 / p95 | 1432 / 2603 ms |
| Tokens in / out | 14162 / 1263 |
| Chat cost | $0.0020 |
| Answers using the reranked order | 0 |

## Documents

| File | Status | Chunks |
|---|---|---|
| remote-work-policy.pdf | ready | 2 |
| expense-policy.pdf | ready | 2 |
| parental-leave-policy.md | ready | 4 |
| office-handbook.txt | ready | 1 |

## Questions

| Question | Category | Expected | Outcome | hit@k | MRR | Refusal ok | Citations valid | Cited | Latency | Tokens in/out | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `coworking_two_sources` | two_sources | answered | answered | 100% | 0.75 | - | yes | 2 | 2603 ms | 1295/185 | $0.0002 |
| `exact_term_amount` | exact_term | answered | answered | 100% | 1.00 | - | yes | 1 | 1609 ms | 1291/135 | $0.0002 |
| `coworking_approval_notice` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 1510 ms | 1368/103 | $0.0002 |
| `expense_submission_deadline` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 1381 ms | 1281/109 | $0.0002 |
| `parental_leave_duration` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 1465 ms | 1436/108 | $0.0002 |
| `parental_leave_eligibility` | single_source | answered | answered | 100% | 0.62 | - | yes | 2 | 1452 ms | 1219/124 | $0.0002 |
| `contractor_parental_leave` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 1367 ms | 1370/104 | $0.0002 |
| `office_opening_hours` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 1435 ms | 1193/102 | $0.0002 |
| `meeting_room_booking` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 1332 ms | 1124/115 | $0.0002 |
| `leave_split_not_covered` | not_covered | insufficient_evidence | insufficient_evidence | n/a | n/a | yes | - | 0 | 1380 ms | 1222/89 | $0.0002 |
| `home_office_equipment` | not_covered | insufficient_evidence | insufficient_evidence | n/a | n/a | yes | - | 0 | 1432 ms | 1363/89 | $0.0002 |
| `unrelated_capital` | unrelated | insufficient_evidence | insufficient_evidence | n/a | n/a | yes | - | 0 | 508 ms | 0/0 | $0.0000 |
| `unrelated_recipe` | unrelated | insufficient_evidence | insufficient_evidence | n/a | n/a | yes | - | 0 | 538 ms | 0/0 | $0.0000 |
