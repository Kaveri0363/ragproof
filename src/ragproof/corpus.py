"""Corpus loading and chunking."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ragproof.text import split_sentences, tokenize


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    text: str
    path: Optional[str] = None


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    position: int

    @property
    def citation(self) -> str:
        return f"[{self.doc_id}]"


@dataclass
class Corpus:
    documents: List[Document]
    chunks: List[Chunk] = field(default_factory=list)

    def by_id(self) -> Dict[str, Document]:
        return {d.doc_id: d for d in self.documents}

    def chunk_index(self) -> Dict[str, Chunk]:
        return {c.chunk_id: c for c in self.chunks}

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self.documents)


def _read_markdown(path: str) -> Document:
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    doc_id = os.path.splitext(os.path.basename(path))[0]
    lines = raw.strip().splitlines()
    title = doc_id
    if lines and lines[0].startswith("#"):
        title = lines[0].lstrip("#").strip()
        lines = lines[1:]
    return Document(doc_id=doc_id, title=title, text="\n".join(lines).strip(), path=path)


def load_corpus(directory: str) -> Corpus:
    """Load every ``.md`` / ``.txt`` file in *directory* as one document."""
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"corpus directory not found: {directory}")
    docs: List[Document] = []
    for name in sorted(os.listdir(directory)):
        if name.startswith("."):
            continue
        if not name.endswith((".md", ".txt")):
            continue
        docs.append(_read_markdown(os.path.join(directory, name)))
    if not docs:
        raise ValueError(f"no .md or .txt documents found in {directory}")
    return Corpus(documents=docs)


def chunk_document(
    doc: Document,
    *,
    size: int = 120,
    overlap: int = 30,
    strategy: str = "sentence",
) -> List[Chunk]:
    """Split a document into overlapping chunks.

    ``size`` and ``overlap`` are measured in whitespace tokens. Two strategies:

    ``fixed``
        A sliding window over the token stream. Fast, but happily cuts a
        sentence in half.
    ``sentence``
        Greedily packs whole sentences up to ``size`` tokens, then backs up by
        roughly ``overlap`` tokens' worth of trailing sentences. Chunk
        boundaries stay readable, which measurably helps the judge and any
        downstream generator.
    """
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must satisfy 0 <= overlap < size")

    if strategy == "fixed":
        pieces = _fixed_windows(doc.text, size, overlap)
    elif strategy == "sentence":
        pieces = _sentence_windows(doc.text, size, overlap)
    else:
        raise ValueError(f"unknown chunking strategy: {strategy}")

    return [
        Chunk(
            chunk_id=f"{doc.doc_id}::{i}",
            doc_id=doc.doc_id,
            title=doc.title,
            text=piece,
            position=i,
        )
        for i, piece in enumerate(pieces)
    ]


def _fixed_windows(text: str, size: int, overlap: int) -> List[str]:
    words = text.split()
    if not words:
        return []
    step = size - overlap
    out: List[str] = []
    for start in range(0, len(words), step):
        window = words[start : start + size]
        if not window:
            break
        out.append(" ".join(window))
        if start + size >= len(words):
            break
    return out


def _sentence_windows(text: str, size: int, overlap: int) -> List[str]:
    sentences = split_sentences(text)
    if not sentences:
        return []
    out: List[str] = []
    current: List[str] = []
    current_len = 0
    for sent in sentences:
        sent_len = len(sent.split())
        if current and current_len + sent_len > size:
            out.append(" ".join(current))
            carry: List[str] = []
            carry_len = 0
            for prev in reversed(current):
                prev_len = len(prev.split())
                if carry_len + prev_len > overlap:
                    break
                carry.insert(0, prev)
                carry_len += prev_len
            current = carry
            current_len = carry_len
        current.append(sent)
        current_len += sent_len
    if current:
        out.append(" ".join(current))
    return out


def build_chunks(corpus: Corpus, **kwargs) -> Corpus:
    """Return a new Corpus with ``chunks`` populated."""
    chunks: List[Chunk] = []
    for doc in corpus.documents:
        chunks.extend(chunk_document(doc, **kwargs))
    return Corpus(documents=corpus.documents, chunks=chunks)


def corpus_stats(corpus: Corpus) -> Dict[str, float]:
    lengths = [len(tokenize(c.text)) for c in corpus.chunks] or [0]
    return {
        "documents": len(corpus.documents),
        "chunks": len(corpus.chunks),
        "mean_chunk_tokens": round(sum(lengths) / len(lengths), 1),
        "max_chunk_tokens": max(lengths),
    }
