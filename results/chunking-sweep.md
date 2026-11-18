# ragproof — `chunking-sweep`

_18 documents · 52 labelled questions · k=5 · generated 2026-08-28 12:31 UTC_

## Leaderboard

| System | Recall@k | MRR | nDCG@k | Precision@k | Grounded | Cite prec. | Answer F1 | Abstain acc. | Latency (ms) |
|---|---|---|---|---|---|---|---|---|---|
| `chunk-40` | 0.957 | 0.958 | 0.935 | 0.519 | 0.996 | 1.000 | 0.365 | 0.600 | 1.5 |
| `chunk-120` | 0.936 | 0.968 | 0.936 | 0.271 | 0.999 | 1.000 | 0.376 | 0.600 | 2.0 |
| `chunk-200` | 0.936 | 0.943 | 0.918 | 0.210 | 1.000 | 1.000 | 0.366 | 0.600 | 2.6 |
| `chunk-320` | 0.936 | 0.943 | 0.918 | 0.204 | 1.000 | 1.000 | 0.361 | 0.600 | 2.5 |
| `chunk-80` | 0.915 | 0.947 | 0.915 | 0.338 | 1.000 | 1.000 | 0.379 | 0.600 | 1.8 |

**`chunk-40` leads `chunk-80` by +0.042 Recall@k.**

## Configurations

- `chunk-40` — hybrid, chunk 40/10 sentence, rerank:lexical · 108 chunks · index 24 ms
- `chunk-120` — hybrid, chunk 120/30 sentence, rerank:lexical · 36 chunks · index 16 ms
- `chunk-200` — hybrid, chunk 200/50 sentence, rerank:lexical · 19 chunks · index 14 ms
- `chunk-320` — hybrid, chunk 320/80 sentence, rerank:lexical · 18 chunks · index 13 ms
- `chunk-80` — hybrid, chunk 80/20 sentence, rerank:lexical · 56 chunks · index 25 ms

## Recall@k by question type

| System | lookup (19) | multi-doc (6) | paraphrase (9) | reasoning (13) |
|---|---|---|---|---|
| `chunk-40` | 1.000 | 0.667 | 1.000 | 1.000 |
| `chunk-120` | 1.000 | 0.667 | 1.000 | 0.923 |
| `chunk-200` | 1.000 | 0.667 | 1.000 | 0.923 |
| `chunk-320` | 1.000 | 0.667 | 1.000 | 0.923 |
| `chunk-80` | 0.947 | 0.667 | 1.000 | 0.923 |

## Hardest questions

Questions the leading system failed to retrieve any gold document for:

- _None — the leading system retrieved a gold document for every question._

