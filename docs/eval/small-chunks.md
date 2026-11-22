# RAG evaluation — `small-chunks`

Baseline with chunks of 120/20 characters — fixture pages and sections are under 300 characters, so only chunks this small split them (closer to one sentence per chunk).

- Run: 2026-11-22 22:17 UTC
- Dataset: `backend/eval/dataset.yaml` (sha256 `18cf4aa7427b`)
- Settings: `chat_provider=anthropic`, `chat_model=claude-haiku-5-5`, `embedding_model=text-embedding-3-small`, `chunk_size=120`, `chunk_overlap=20`, `retrieval_candidates=20`, `retrieval_top_k=6`, `min_relevance=0.3`, `rerank_enabled=False`, `rerank_top_n=4`, `context_token_budget=3000`, `answer_max_tokens=800`, `chat_temperature=None`

## Summary

| Metric | Value |
|---|---|
| Questions (errors) | 13 (0) |
| Outcome accuracy | 100% |
| Retrieval hit@k (mean) | 100% |
| Expected-source MRR | 0.77 |
| Correct refusal rate | 100% |
| Citation validity | 78% |
| Citation recall (mean) | 100% |
| Latency p50 / p95 | 1514 / 2570 ms |
| Tokens in / out | 14006 / 1260 |
| Chat cost | $0.0020 |
| Answers using the reranked order | 0 |

## Documents

| File | Status | Chunks |
|---|---|---|
| remote-work-policy.pdf | ready | 5 |
| expense-policy.pdf | ready | 3 |
| parental-leave-policy.md | ready | 5 |
| office-handbook.txt | ready | 4 |

## Questions

| Question | Category | Expected | Outcome | hit@k | MRR | Refusal ok | Citations valid | Cited | Latency | Tokens in/out | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `coworking_two_sources` | two_sources | answered | answered | 100% | 0.75 | - | **no** | 3 | 2570 ms | 1300/162 | $0.0002 |
| `exact_term_amount` | exact_term | answered | answered | 100% | 1.00 | - | yes | 1 | 1514 ms | 1304/135 | $0.0002 |
| `coworking_approval_notice` | single_source | answered | answered | 100% | 0.50 | - | **no** | 2 | 1541 ms | 1282/123 | $0.0002 |
| `expense_submission_deadline` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 1498 ms | 1234/110 | $0.0002 |
| `parental_leave_duration` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 1389 ms | 1325/109 | $0.0002 |
| `parental_leave_eligibility` | single_source | answered | answered | 100% | 0.23 | - | yes | 2 | 2332 ms | 1323/124 | $0.0002 |
| `contractor_parental_leave` | single_source | answered | answered | 100% | 0.50 | - | yes | 1 | 1659 ms | 1336/103 | $0.0002 |
| `office_opening_hours` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 1472 ms | 1255/101 | $0.0002 |
| `meeting_room_booking` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 1567 ms | 1076/115 | $0.0002 |
| `leave_split_not_covered` | not_covered | insufficient_evidence | insufficient_evidence | n/a | n/a | yes | - | 0 | 1550 ms | 1332/89 | $0.0002 |
| `home_office_equipment` | not_covered | insufficient_evidence | insufficient_evidence | n/a | n/a | yes | - | 0 | 1462 ms | 1239/89 | $0.0002 |
| `unrelated_capital` | unrelated | insufficient_evidence | insufficient_evidence | n/a | n/a | yes | - | 0 | 463 ms | 0/0 | $0.0000 |
| `unrelated_recipe` | unrelated | insufficient_evidence | insufficient_evidence | n/a | n/a | yes | - | 0 | 514 ms | 0/0 | $0.0000 |
