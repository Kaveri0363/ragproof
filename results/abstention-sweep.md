# ragproof — `abstention-sweep`

_18 documents · 52 labelled questions · k=3 · generated 2026-08-28 12:33 UTC_

## Leaderboard

| System | Recall@k | MRR | nDCG@k | Precision@k | Grounded | Cite prec. | Answer F1 | Abstain acc. | Answer rate | Latency (ms) |
|---|---|---|---|---|---|---|---|---|---|---|
| `threshold-0.15` | 0.957 | 0.989 | 0.959 | 0.486 | 0.999 | 1.000 | 0.371 | 0.200 | 1.000 | 0.4 |
| `threshold-0.25` | 0.957 | 0.989 | 0.959 | 0.486 | 0.999 | 1.000 | 0.378 | 0.600 | 0.979 | 0.3 |
| `threshold-0.34` | 0.957 | 0.989 | 0.959 | 0.486 | 0.999 | 1.000 | 0.386 | 0.600 | 0.702 | 0.4 |
| `threshold-0.45` | 0.957 | 0.989 | 0.959 | 0.486 | 0.998 | 1.000 | 0.452 | 1.000 | 0.425 | 0.4 |
| `threshold-0.60` | 0.957 | 0.989 | 0.959 | 0.486 | 0.996 | 1.000 | 0.497 | 1.000 | 0.213 | 0.3 |

**`threshold-0.15` leads `threshold-0.60` by +0.787 Answer rate.**

## Configurations

- `threshold-0.15` — bm25, chunk 120/30 sentence · 36 chunks · index 3 ms
- `threshold-0.25` — bm25, chunk 120/30 sentence · 36 chunks · index 2 ms
- `threshold-0.34` — bm25, chunk 120/30 sentence · 36 chunks · index 2 ms
- `threshold-0.45` — bm25, chunk 120/30 sentence · 36 chunks · index 3 ms
- `threshold-0.60` — bm25, chunk 120/30 sentence · 36 chunks · index 2 ms

## Recall@k by question type

| System | lookup (19) | multi-doc (6) | paraphrase (9) | reasoning (13) |
|---|---|---|---|---|
| `threshold-0.15` | 1.000 | 0.667 | 1.000 | 1.000 |
| `threshold-0.25` | 1.000 | 0.667 | 1.000 | 1.000 |
| `threshold-0.34` | 1.000 | 0.667 | 1.000 | 1.000 |
| `threshold-0.45` | 1.000 | 0.667 | 1.000 | 1.000 |
| `threshold-0.60` | 1.000 | 0.667 | 1.000 | 1.000 |

## Hardest questions

Questions the leading system failed to retrieve any gold document for:

- _None — the leading system retrieved a gold document for every question._

