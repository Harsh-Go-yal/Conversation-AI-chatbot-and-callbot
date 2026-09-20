# Evaluation results
Run: 20260920-133546 · 8 questions · 8 passed

| Metric | Value | n |
|---|---|---|
| retrieval_hit | 1.00 | 5 |
| routing | 1.00 | 3 |
| conflict_recall | 1.00 | 1 |
| access |  | 0 |
| customer_public_only |  | 0 |
| answer_hit | 1.00 | 3 |
| intent | 1.00 | 3 |
| format | 1.00 | 4 |
| json_valid | 1.00 | 1 |
| faithfulness (LLM-judge) | 1.0 | 5 |
| leak test: restricted chunks sent to cloud | **0** | 17 OpenAI calls / 3 local |
| latency p50 / p95 (s) | 23.9 / 139.7 | 8 |
| stage medians (ms) | {'router': 2304, 'retrieval': 7515, 'conflicts': 972, 'reasoner': 4483} | |

## Per question

| id | pass | s | llm | format | conflicts | failed checks |
|---|---|---|---|---|---|---|
| fin04 | ✅ | 139.7 | local | text | superseded |  |
| leg05 | ✅ | 160.3 | local | text |  |  |
| pri03 | ✅ | 108.2 | local | text |  |  |
| sup10 | ✅ | 34.8 | openai | email | superseded, superseded |  |
| mt01 | ✅ | 13.1 | openai | text | superseded |  |
| mt02 | ✅ | 1.9 | openai | json | superseded |  |
| mt03 | ✅ | 2.5 | openai | excel | superseded |  |
| mt04 | ✅ | 4.4 | openai | email | superseded |  |