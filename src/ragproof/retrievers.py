"""Retrieval strategies: BM25, dense vectors, and reciprocal-rank fusion.

BM25 is implemented here rather than pulled from a library. It is ~40 lines,
and owning it means the scoring is inspectable when a result looks wrong —
which, during evaluation work, it regularly does.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import numpy as np

from ragproof.corpus import Chunk
from ragproof.embeddings import Embedder, build_embedder
from ragproof.text import tokenize


@dataclass(frozen=True)
class Retrieved:
    chunk_id: str
    doc_id: str
    score: float
    rank: int
    text: str
    title: str = ""


class Retriever:
    name = "retriever"

    def index(self, chunks: Sequence[Chunk]) -> "Retriever":  # pragma: no cover - abstract
        raise NotImplementedError

    def search(self, query: str, k: int = 5) -> List[Retrieved]:  # pragma: no cover
        raise NotImplementedError


def _to_results(chunks: Sequence[Chunk], scored: Sequence[tuple]) -> List[Retrieved]:
    out: List[Retrieved] = []
    for rank, (idx, score) in enumerate(scored, start=1):
        c = chunks[idx]
        out.append(
            Retrieved(
                chunk_id=c.chunk_id,
                doc_id=c.doc_id,
                score=float(score),
                rank=rank,
                text=c.text,
                title=c.title,
            )
        )
    return out


class BM25Retriever(Retriever):
    """Okapi BM25 over chunk text."""

    name = "bm25"

    def __init__(self, k1: float = 1.5, b: float = 0.75, drop_stopwords: bool = True) -> None:
        self.k1 = k1
        self.b = b
        self.drop_stopwords = drop_stopwords
        self._chunks: List[Chunk] = []
        self._tf: List[Dict[str, int]] = []
        self._lengths: List[int] = []
        self._idf: Dict[str, float] = {}
        self._avgdl = 0.0

    def index(self, chunks: Sequence[Chunk]) -> "BM25Retriever":
        self._chunks = list(chunks)
        self._tf = []
        self._lengths = []
        df: Dict[str, int] = defaultdict(int)
        for chunk in self._chunks:
            # Index the title with the body. A chunk taken from the middle of a
            # document loses the one line that says what the document is about,
            # and that costs real recall — q014 in the bundled eval set is
            # exactly this failure.
            toks = tokenize(f"{chunk.title}. {chunk.text}", drop_stopwords=self.drop_stopwords)
            counts: Dict[str, int] = defaultdict(int)
            for tok in toks:
                counts[tok] += 1
            self._tf.append(dict(counts))
            self._lengths.append(len(toks))
            for tok in counts:
                df[tok] += 1
        n = max(len(self._chunks), 1)
        self._idf = {t: math.log(1.0 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self._avgdl = (sum(self._lengths) / n) if self._lengths else 0.0
        return self

    def search(self, query: str, k: int = 5) -> List[Retrieved]:
        q_tokens = tokenize(query, drop_stopwords=self.drop_stopwords)
        scores = np.zeros(len(self._chunks), dtype=np.float64)
        for i, tf in enumerate(self._tf):
            dl = self._lengths[i] or 1
            total = 0.0
            for tok in q_tokens:
                f = tf.get(tok)
                if not f:
                    continue
                idf = self._idf.get(tok, 0.0)
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self._avgdl or 1.0))
                total += idf * (f * (self.k1 + 1)) / denom
            scores[i] = total
        return _to_results(self._chunks, _top_k(scores, k))


class DenseRetriever(Retriever):
    """Cosine similarity over embedded chunks."""

    name = "dense"

    def __init__(self, embedder: Optional[dict] = None) -> None:
        self.embedder: Embedder = build_embedder(embedder)
        self._chunks: List[Chunk] = []
        self._matrix: Optional[np.ndarray] = None

    def index(self, chunks: Sequence[Chunk]) -> "DenseRetriever":
        self._chunks = list(chunks)
        texts = [f"{c.title}. {c.text}" for c in self._chunks]
        self.embedder.fit(texts)
        self._matrix = self.embedder.encode(texts)
        return self

    def search(self, query: str, k: int = 5) -> List[Retrieved]:
        if self._matrix is None:
            raise RuntimeError("index() must be called before search()")
        q = self.embedder.encode([query])[0]
        scores = self._matrix @ q
        return _to_results(self._chunks, _top_k(scores, k))


class HybridRetriever(Retriever):
    """Reciprocal rank fusion of several retrievers.

    RRF is used rather than a weighted sum of raw scores because BM25 scores
    and cosine similarities live on different scales; fusing ranks sidesteps
    the normalisation problem entirely and is hard to overfit.
    """

    name = "hybrid"

    def __init__(
        self,
        retrievers: Optional[Sequence[dict]] = None,
        rrf_k: int = 60,
        candidate_multiplier: int = 4,
    ) -> None:
        specs = retrievers or [{"kind": "bm25"}, {"kind": "dense"}]
        self.members = [build_retriever(s) for s in specs]
        self.rrf_k = rrf_k
        self.candidate_multiplier = candidate_multiplier
        self._chunks: List[Chunk] = []

    def index(self, chunks: Sequence[Chunk]) -> "HybridRetriever":
        self._chunks = list(chunks)
        for member in self.members:
            member.index(chunks)
        return self

    def search(self, query: str, k: int = 5) -> List[Retrieved]:
        depth = max(k * self.candidate_multiplier, k)
        fused: Dict[str, float] = defaultdict(float)
        seen: Dict[str, Retrieved] = {}
        for member in self.members:
            for hit in member.search(query, depth):
                fused[hit.chunk_id] += 1.0 / (self.rrf_k + hit.rank)
                seen.setdefault(hit.chunk_id, hit)
        ordered = sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
        return [
            Retrieved(
                chunk_id=cid,
                doc_id=seen[cid].doc_id,
                score=score,
                rank=rank,
                text=seen[cid].text,
                title=seen[cid].title,
            )
            for rank, (cid, score) in enumerate(ordered, start=1)
        ]


def _top_k(scores: np.ndarray, k: int) -> List[tuple]:
    if len(scores) == 0:
        return []
    k = min(k, len(scores))
    # argsort on (-score, index) keeps ties deterministic across runs.
    order = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), i))[:k]
    return [(i, float(scores[i])) for i in order]


_REGISTRY = {
    "bm25": BM25Retriever,
    "dense": DenseRetriever,
    "hybrid": HybridRetriever,
}


def build_retriever(spec: Optional[dict]) -> Retriever:
    spec = dict(spec or {})
    kind = spec.pop("kind", "bm25")
    if kind not in _REGISTRY:
        raise ValueError(f"unknown retriever '{kind}' (have: {sorted(_REGISTRY)})")
    return _REGISTRY[kind](**spec)
