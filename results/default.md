# ragproof — `default`

_18 documents · 52 labelled questions · k=3 · generated 2026-08-28 12:35 UTC_

## Leaderboard

| System | Recall@k | MRR | nDCG@k | Precision@k | Grounded | Cite prec. | Answer F1 | Abstain acc. | Answer rate | Latency (ms) |
|---|---|---|---|---|---|---|---|---|---|---|
| `bm25-baseline` | 0.957 | 0.989 | 0.959 | 0.486 | 0.999 | 1.000 | 0.378 | 0.600 | 0.979 | 0.3 |
| `bm25-fixed-chunks` | 0.957 | 0.989 | 0.959 | 0.493 | 0.999 | 1.000 | 0.367 | 0.600 | 0.979 | 0.3 |
| `bm25-small-chunks` | 0.925 | 0.957 | 0.922 | 0.684 | 0.998 | 1.000 | 0.383 | 0.600 | 0.979 | 0.3 |
| `hybrid-rrf-reranked` | 0.925 | 0.968 | 0.930 | 0.461 | 0.999 | 1.000 | 0.375 | 0.600 | 0.979 | 1.8 |
| `hybrid-rrf` | 0.915 | 0.933 | 0.895 | 0.429 | 0.999 | 1.000 | 0.380 | 0.600 | 0.979 | 0.7 |
| `dense-hashing` | 0.851 | 0.816 | 0.792 | 0.397 | 0.999 | 1.000 | 0.395 | 0.600 | 0.915 | 0.5 |

**`bm25-baseline` leads `dense-hashing` by +0.106 Recall@k.**

## Configurations

- `bm25-baseline` — bm25, chunk 120/30 sentence · 36 chunks · index 3 ms · sparse lexical retrieval, sentence-aware chunks
- `bm25-fixed-chunks` — bm25, chunk 120/30 fixed · 36 chunks · index 2 ms · same size, naive windowing — isolates the cost of cutting sentences
- `bm25-small-chunks` — bm25, chunk 60/15 sentence · 75 chunks · index 3 ms · smaller chunks — higher precision, more boundary loss
- `hybrid-rrf-reranked` — hybrid, chunk 120/30 sentence, rerank:lexical · 36 chunks · index 16 ms · fusion plus a second-stage reranker over the top 20 candidates
- `hybrid-rrf` — hybrid, chunk 120/30 sentence · 36 chunks · index 16 ms · reciprocal rank fusion of sparse and dense
- `dense-hashing` — dense, chunk 120/30 sentence · 36 chunks · index 15 ms · deterministic hashed TF-IDF embeddings, cosine similarity

## Recall@k by question type

| System | lookup (19) | multi-doc (6) | paraphrase (9) | reasoning (13) |
|---|---|---|---|---|
| `bm25-baseline` | 1.000 | 0.667 | 1.000 | 1.000 |
| `bm25-fixed-chunks` | 1.000 | 0.667 | 1.000 | 1.000 |
| `bm25-small-chunks` | 0.947 | 0.583 | 1.000 | 1.000 |
| `hybrid-rrf-reranked` | 1.000 | 0.583 | 1.000 | 0.923 |
| `hybrid-rrf` | 1.000 | 0.500 | 1.000 | 0.923 |
| `dense-hashing` | 0.947 | 0.500 | 0.778 | 0.923 |

## Hardest questions

Questions the leading system failed to retrieve any gold document for:

- _None — the leading system retrieved a gold document for every question._

