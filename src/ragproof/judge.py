"""Groundedness judging — does the answer actually follow from the context?

Retrieval metrics tell you whether the right document was found. They say
nothing about whether the answer invented something. This module measures the
second thing, deterministically by default:

``groundedness``
    Fraction of the answer's content bigrams that appear in the retrieved
    context. Bigrams rather than unigrams because unigram overlap is trivially
    gamed by any answer that reuses the question's vocabulary.
``citation_precision``
    Fraction of cited document ids that were actually retrieved. A citation to
    a document the pipeline never saw is a fabricated citation.
``unsupported_sentences``
    The specific sentences that failed, so a regression is debuggable rather
    than just a number that went down.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from ragproof.text import ngrams, tokenize

_CITE_RE = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9._-]*)\]")


@dataclass
class Verdict:
    groundedness: float
    citation_precision: float
    unsupported_sentences: List[str] = field(default_factory=list)
    detail: Dict[str, float] = field(default_factory=dict)


class Judge:
    name = "judge"

    def score(self, question: str, answer: str, contexts: Sequence[str], cited=()) -> Verdict:
        raise NotImplementedError  # pragma: no cover - abstract


class OverlapJudge(Judge):
    """Deterministic n-gram-entailment proxy. No API key, no sampling noise."""

    name = "overlap"

    def __init__(self, n: int = 2, sentence_threshold: float = 0.5) -> None:
        self.n = n
        self.sentence_threshold = sentence_threshold

    def _support(self, text: str, context_grams: set) -> float:
        grams = ngrams(tokenize(text, drop_stopwords=True), self.n)
        if not grams:
            toks = tokenize(text, drop_stopwords=True)
            if not toks:
                return 1.0
            return sum(1 for t in toks if (t,) in context_grams) / len(toks)
        return sum(1 for g in grams if g in context_grams) / len(grams)

    def score(
        self,
        question: str,
        answer: str,
        contexts: Sequence[str],
        cited: Sequence[str] = (),
        retrieved_doc_ids: Sequence[str] = (),
    ) -> Verdict:
        joined = " ".join(contexts)
        ctx_tokens = tokenize(joined, drop_stopwords=True)
        context_grams = set(ngrams(ctx_tokens, self.n)) | {(t,) for t in ctx_tokens}

        clean = _CITE_RE.sub(" ", answer)
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
        supports = [self._support(s, context_grams) for s in sentences] or [
            self._support(clean, context_grams)
        ]
        unsupported = [
            s for s, sup in zip(sentences, supports) if sup < self.sentence_threshold
        ]
        groundedness = sum(supports) / len(supports)

        cited_ids = list(cited) or _CITE_RE.findall(answer)
        if cited_ids:
            allowed = set(retrieved_doc_ids)
            valid = [c for c in cited_ids if not allowed or c in allowed]
            citation_precision = len(valid) / len(cited_ids)
        else:
            citation_precision = 0.0

        return Verdict(
            groundedness=round(groundedness, 4),
            citation_precision=round(citation_precision, 4),
            unsupported_sentences=unsupported,
            detail={"sentences": len(sentences), "citations": len(cited_ids)},
        )


class LLMJudge(Judge):  # pragma: no cover - network path
    """LLM-as-judge with a strict rubric. Optional; requires ``ragproof[llm]``.

    Kept behind a flag on purpose: an LLM judge is non-deterministic and costs
    money per run, so it belongs in a nightly job, not in the CI gate.
    """

    name = "llm"

    RUBRIC = (
        "You are grading whether an ANSWER is fully supported by CONTEXT.\n"
        "Reply with a single number between 0 and 1 and nothing else.\n"
        "1.0 = every claim is directly stated in CONTEXT.\n"
        "0.0 = the answer asserts something CONTEXT does not support.\n\n"
        "CONTEXT:\n{context}\n\nQUESTION: {question}\nANSWER: {answer}\nSCORE:"
    )

    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model

    def score(self, question, answer, contexts, cited=(), retrieved_doc_ids=()) -> Verdict:
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = client.messages.create(
            model=self.model,
            max_tokens=8,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": self.RUBRIC.format(
                        context="\n\n".join(contexts), question=question, answer=answer
                    ),
                }
            ],
        )
        raw = "".join(b.text for b in msg.content if b.type == "text").strip()
        try:
            value = max(0.0, min(1.0, float(raw.split()[0])))
        except (ValueError, IndexError):
            value = 0.0
        overlap = OverlapJudge().score(question, answer, contexts, cited, retrieved_doc_ids)
        return Verdict(
            groundedness=value,
            citation_precision=overlap.citation_precision,
            unsupported_sentences=overlap.unsupported_sentences,
            detail={"llm_raw": raw},
        )


_REGISTRY = {"overlap": OverlapJudge, "llm": LLMJudge}


def build_judge(spec: Optional[dict]) -> Judge:
    spec = dict(spec or {})
    kind = spec.pop("kind", "overlap")
    if kind not in _REGISTRY:
        raise ValueError(f"unknown judge '{kind}' (have: {sorted(_REGISTRY)})")
    return _REGISTRY[kind](**spec)
