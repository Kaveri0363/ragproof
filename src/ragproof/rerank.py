"""Rerankers: cheap second-stage scoring over the retriever's candidate set.

First-stage retrieval optimises recall at depth; reranking optimises precision
at the top. Splitting the two is the single highest-leverage structural choice
in a production RAG pipeline, so it is a first-class, ablatable stage here.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from ragproof.retrievers import Retrieved
from ragproof.text import tokenize


class Reranker:
    name = "reranker"

    def rerank(self, query: str, hits: Sequence[Retrieved], k: int) -> List[Retrieved]:
        raise NotImplementedError  # pragma: no cover - abstract


class NoopReranker(Reranker):
    name = "none"

    def rerank(self, query: str, hits: Sequence[Retrieved], k: int) -> List[Retrieved]:
        return list(hits[:k])


class LexicalOverlapReranker(Reranker):
    """Rescore candidates by query-term coverage, proximity, and first-stage rank.

    Three signals, deliberately:

    ``coverage``
        Fraction of the query's distinct content terms present in the chunk.
    ``proximity``
        How tightly those terms cluster. A chunk mentioning "sanctions" in one
        paragraph and "timeout" in another is worse than one sentence covering
        both, and coverage alone cannot tell them apart.
    ``prior``
        The first-stage rank, folded back in as ``1 / (rrf_k + rank)``.

    The prior matters more than it looks. A reranker that throws away the
    first stage's ordering discards a well-calibrated global signal (IDF, in
    BM25's case) and replaces it with a local one — which measurably *lowers*
    recall. Reranking should refine an ordering, not recompute it from nothing.
    """

    name = "lexical"

    def __init__(
        self,
        coverage_weight: float = 0.55,
        proximity_weight: float = 0.15,
        prior_weight: float = 0.30,
        prior_k: int = 10,
    ) -> None:
        self.coverage_weight = coverage_weight
        self.proximity_weight = proximity_weight
        self.prior_weight = prior_weight
        self.prior_k = prior_k

    def _score(self, query: str, text: str, rank: int) -> float:
        q_terms = list(dict.fromkeys(tokenize(query, drop_stopwords=True)))
        if not q_terms:
            return 0.0
        doc_tokens = tokenize(text, drop_stopwords=True)
        positions: dict = {}
        for i, tok in enumerate(doc_tokens):
            positions.setdefault(tok, i)
        present = [t for t in q_terms if t in positions]
        coverage = len(present) / len(q_terms)
        if len(present) > 1:
            span = max(positions[t] for t in present) - min(positions[t] for t in present)
            proximity = coverage / (1.0 + span / (10.0 * len(present)))
        else:
            proximity = 0.0
        prior = self.prior_k / (self.prior_k + rank - 1)
        return (
            self.coverage_weight * coverage
            + self.proximity_weight * proximity
            + self.prior_weight * prior
        )

    def rerank(self, query: str, hits: Sequence[Retrieved], k: int) -> List[Retrieved]:
        scored = [(self._score(query, f"{h.title}. {h.text}", h.rank), h) for h in hits]
        scored.sort(key=lambda pair: (-pair[0], pair[1].rank))
        return [
            Retrieved(
                chunk_id=h.chunk_id,
                doc_id=h.doc_id,
                score=round(score, 6),
                rank=i,
                text=h.text,
                title=h.title,
            )
            for i, (score, h) in enumerate(scored[:k], start=1)
        ]


class CrossEncoderReranker(Reranker):
    """Optional real cross-encoder. ``pip install 'ragproof[dense]'``."""

    name = "cross-encoder"

    def __init__(self, model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model
        self._model = None

    def _load(self):  # pragma: no cover - optional path
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise ImportError(
                    "CrossEncoderReranker needs: pip install 'ragproof[dense]'"
                ) from exc
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query: str, hits, k: int):  # pragma: no cover - optional path
        model = self._load()
        pairs = [(query, f"{h.title}. {h.text}") for h in hits]
        scores = model.predict(pairs)
        order = sorted(range(len(hits)), key=lambda i: -float(scores[i]))[:k]
        return [
            Retrieved(
                chunk_id=hits[i].chunk_id,
                doc_id=hits[i].doc_id,
                score=float(scores[i]),
                rank=rank,
                text=hits[i].text,
                title=hits[i].title,
            )
            for rank, i in enumerate(order, start=1)
        ]


_REGISTRY = {
    "none": NoopReranker,
    "lexical": LexicalOverlapReranker,
    "cross-encoder": CrossEncoderReranker,
}


def build_reranker(spec: Optional[dict]) -> Reranker:
    spec = dict(spec or {})
    kind = spec.pop("kind", "none")
    if kind not in _REGISTRY:
        raise ValueError(f"unknown reranker '{kind}' (have: {sorted(_REGISTRY)})")
    return _REGISTRY[kind](**spec)
