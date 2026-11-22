# RAG evaluation — `rerank`

Baseline with the LLM reranker on (RERANK_ENABLED=true, top 4) — one extra chat call per question with evidence.

- Run: 2026-11-22 22:16 UTC
- Dataset: `backend/eval/dataset.yaml` (sha256 `18cf4aa7427b`)
- Settings: `chat_provider=anthropic`, `chat_model=claude-haiku-5-5`, `embedding_model=text-embedding-3-small`, `chunk_size=1000`, `chunk_overlap=150`, `retrieval_candidates=20`, `retrieval_top_k=6`, `min_relevance=0.3`, `rerank_enabled=True`, `rerank_top_n=4`, `context_token_budget=3000`, `answer_max_tokens=800`, `chat_temperature=None`

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
| Latency p50 / p95 | 2336 / 16733 ms |
| Tokens in / out | 23602 / 1772 |
| Chat cost | $0.0032 |
| Answers using the reranked order | 11 |

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
| `coworking_two_sources` | two_sources | answered | answered | 100% | 0.75 | - | yes | 2 | 3535 ms | 2229/238 | $0.0003 |
| `exact_term_amount` | exact_term | answered | answered | 100% | 1.00 | - | yes | 1 | 2248 ms | 2030/181 | $0.0003 |
| `coworking_approval_notice` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 2248 ms | 2121/142 | $0.0003 |
| `expense_submission_deadline` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 2336 ms | 1996/149 | $0.0003 |
| `parental_leave_duration` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 2403 ms | 2324/155 | $0.0003 |
| `parental_leave_eligibility` | single_source | answered | answered | 100% | 0.62 | - | yes | 2 | 2158 ms | 2173/177 | $0.0003 |
| `contractor_parental_leave` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 2413 ms | 2326/155 | $0.0003 |
| `office_opening_hours` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 16733 ms | 1943/141 | $0.0003 |
| `meeting_room_booking` | single_source | answered | answered | 100% | 1.00 | - | yes | 1 | 10424 ms | 1883/154 | $0.0003 |
| `leave_split_not_covered` | not_covered | insufficient_evidence | insufficient_evidence | n/a | n/a | yes | - | 0 | 2328 ms | 2179/140 | $0.0003 |
| `home_office_equipment` | not_covered | insufficient_evidence | insufficient_evidence | n/a | n/a | yes | - | 0 | 2839 ms | 2398/140 | $0.0003 |
| `unrelated_capital` | unrelated | insufficient_evidence | insufficient_evidence | n/a | n/a | yes | - | 0 | 560 ms | 0/0 | $0.0000 |
| `unrelated_recipe` | unrelated | insufficient_evidence | insufficient_evidence | n/a | n/a | yes | - | 0 | 513 ms | 0/0 | $0.0000 |
