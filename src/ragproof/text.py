"""Tokenisation and small text helpers.

Deliberately dependency-free: every component in ragproof must be able to run
in CI with no model downloads and no network access, so the tokeniser is a
plain regex one rather than a learned vocabulary.
"""

from __future__ import annotations

import re
from typing import Iterable, List

_WORD_RE = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*")
_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])|\n{2,}")

# Small, explicit stopword list. Kept short on purpose: aggressive stopword
# removal hurts recall on operational documentation, where words like "not"
# and "before" carry real meaning.
STOPWORDS = frozenset(
    """a an and are as at be by for from has have how in into is it its of on or
    that the this to was were what when where which who will with you your""".split()
)


def tokenize(text: str, *, drop_stopwords: bool = False) -> List[str]:
    """Lowercase word tokens. Keeps dotted/underscored identifiers intact.

    ``pacs.008`` and ``payment_id`` survive as single tokens, which matters a
    lot when the corpus is technical documentation.
    """
    tokens = _WORD_RE.findall(text.lower())
    if drop_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    return tokens


def split_sentences(text: str) -> List[str]:
    """Cheap sentence splitter good enough for prose and markdown bullets."""
    parts: List[str] = []
    for block in text.split("\n"):
        block = block.strip()
        if not block:
            continue
        for sent in _SENT_RE.split(block):
            sent = sent.strip()
            if sent:
                parts.append(sent)
    return parts


def ngrams(tokens: Iterable[str], n: int) -> List[tuple]:
    toks = list(tokens)
    if n <= 0 or len(toks) < n:
        return []
    return [tuple(toks[i : i + n]) for i in range(len(toks) - n + 1)]
