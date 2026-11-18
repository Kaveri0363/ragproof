"""Retrieval and answer metrics.

Everything here takes plain Python lists so the functions stay unit-testable
without building an index.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Sequence

from ragproof.text import tokenize


def dedupe(doc_ids: Iterable[str]) -> List[str]:
    """Rank-preserving de-duplication: several chunks of one document count once."""
    seen = set()
    out = []
    for doc_id in doc_ids:
        if doc_id not in seen:
            seen.add(doc_id)
            out.append(doc_id)
    return out


def recall_at_k(retrieved: Sequence[str], gold: Sequence[str], k: int) -> float:
    if not gold:
        return 0.0
    top = set(dedupe(retrieved)[:k])
    return len(top & set(gold)) / len(set(gold))


def precision_at_k(retrieved: Sequence[str], gold: Sequence[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top = dedupe(retrieved)[:k]
    if not top:
        return 0.0
    gold_set = set(gold)
    return sum(1 for d in top if d in gold_set) / len(top)


def hit_rate_at_k(retrieved: Sequence[str], gold: Sequence[str], k: int) -> float:
    top = set(dedupe(retrieved)[:k])
    return 1.0 if top & set(gold) else 0.0


def reciprocal_rank(retrieved: Sequence[str], gold: Sequence[str]) -> float:
    gold_set = set(gold)
    for rank, doc_id in enumerate(dedupe(retrieved), start=1):
        if doc_id in gold_set:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: Sequence[str], gold: Sequence[str], k: int) -> float:
    """Binary-relevance nDCG@k."""
    if not gold:
        return 0.0
    gold_set = set(gold)
    top = dedupe(retrieved)[:k]
    dcg = sum(
        (1.0 / math.log2(rank + 1)) for rank, d in enumerate(top, start=1) if d in gold_set
    )
    ideal_hits = min(len(gold_set), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def token_f1(prediction: str, reference: str) -> float:
    """SQuAD-style token overlap F1 — a cheap, deterministic answer-quality floor."""
    pred = tokenize(prediction, drop_stopwords=True)
    ref = tokenize(reference, drop_stopwords=True)
    if not pred or not ref:
        return 1.0 if pred == ref else 0.0
    common: Dict[str, int] = {}
    ref_counts: Dict[str, int] = {}
    for t in ref:
        ref_counts[t] = ref_counts.get(t, 0) + 1
    overlap = 0
    for t in pred:
        if ref_counts.get(t, 0) > 0:
            ref_counts[t] -= 1
            overlap += 1
            common[t] = common.get(t, 0) + 1
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred)
    recall = overlap / len(ref)
    return 2 * precision * recall / (precision + recall)


def aggregate(rows: Sequence[Dict[str, float]]) -> Dict[str, float]:
    """Mean of every numeric key present in *rows*."""
    if not rows:
        return {}
    keys = sorted({k for row in rows for k, v in row.items() if isinstance(v, (int, float))})
    out = {}
    for key in keys:
        vals = [float(row[key]) for row in rows if key in row]
        out[key] = round(sum(vals) / len(vals), 4) if vals else 0.0
    return out
