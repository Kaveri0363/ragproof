"""Embedding backends.

The default backend is a deterministic hashing embedder (a signed random
projection of a TF-IDF bag of words). It is not as good as a trained
sentence encoder, and it is not meant to be: it exists so the whole harness
runs byte-identically in CI with no model download, no GPU and no API key.
Swap in ``SentenceTransformerEmbedder`` and every number in the report moves,
which is exactly the comparison this project is built to make.
"""

from __future__ import annotations

import hashlib
import math
from typing import Dict, List, Optional, Sequence

import numpy as np

from ragproof.text import tokenize


class Embedder:
    """Base interface."""

    name = "embedder"
    dim = 0

    def fit(self, texts: Sequence[str]) -> "Embedder":
        return self

    def encode(self, texts: Sequence[str]) -> np.ndarray:  # pragma: no cover - abstract
        raise NotImplementedError


def _stable_hash(token: str, seed: int) -> int:
    digest = hashlib.blake2b(f"{seed}:{token}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


class HashingEmbedder(Embedder):
    """Signed hashing trick over TF-IDF weighted unigrams (+ optional bigrams).

    Deterministic across processes and Python versions — ``hash()`` is not,
    which is why blake2b is used instead.
    """

    name = "hashing"

    def __init__(
        self,
        dim: int = 512,
        seed: int = 17,
        use_idf: bool = True,
        bigrams: bool = True,
        drop_stopwords: bool = True,
    ) -> None:
        self.dim = dim
        self.seed = seed
        self.use_idf = use_idf
        self.bigrams = bigrams
        self.drop_stopwords = drop_stopwords
        self._idf: Dict[str, float] = {}
        self._default_idf = 1.0

    def _features(self, text: str) -> List[str]:
        toks = tokenize(text, drop_stopwords=self.drop_stopwords)
        feats = list(toks)
        if self.bigrams:
            feats.extend(f"{a}_{b}" for a, b in zip(toks, toks[1:]))
        return feats

    def fit(self, texts: Sequence[str]) -> "HashingEmbedder":
        n = max(len(texts), 1)
        df: Dict[str, int] = {}
        for text in texts:
            for feat in set(self._features(text)):
                df[feat] = df.get(feat, 0) + 1
        self._idf = {f: math.log((n + 1) / (c + 0.5)) + 1.0 for f, c in df.items()}
        self._default_idf = math.log((n + 1) / 0.5) + 1.0
        return self

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            counts: Dict[str, int] = {}
            for feat in self._features(text):
                counts[feat] = counts.get(feat, 0) + 1
            for feat, tf in counts.items():
                weight = (1.0 + math.log(tf)) * (
                    self._idf.get(feat, self._default_idf) if self.use_idf else 1.0
                )
                h = _stable_hash(feat, self.seed)
                idx = h % self.dim
                sign = 1.0 if (h >> 61) & 1 else -1.0
                out[row, idx] += sign * weight
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return out / norms


class SentenceTransformerEmbedder(Embedder):
    """Optional real encoder. ``pip install ragproof[dense]`` to use it."""

    name = "sentence-transformers"

    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model
        self._model = None
        self.dim = 0

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover - optional path
                raise ImportError(
                    "SentenceTransformerEmbedder needs the 'dense' extra: "
                    "pip install 'ragproof[dense]'"
                ) from exc
            self._model = SentenceTransformer(self.model_name)
            self.dim = int(self._model.get_sentence_embedding_dimension())
        return self._model

    def encode(self, texts: Sequence[str]) -> np.ndarray:  # pragma: no cover - optional
        model = self._load()
        vecs = model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vecs, dtype=np.float32)


_REGISTRY = {
    "hashing": HashingEmbedder,
    "sentence-transformers": SentenceTransformerEmbedder,
}


def build_embedder(spec: Optional[dict]) -> Embedder:
    spec = dict(spec or {})
    kind = spec.pop("kind", "hashing")
    if kind not in _REGISTRY:
        raise ValueError(f"unknown embedder '{kind}' (have: {sorted(_REGISTRY)})")
    return _REGISTRY[kind](**spec)
