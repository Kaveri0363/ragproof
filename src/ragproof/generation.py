"""Answer generators.

The default generator is extractive and deterministic: it selects supporting
sentences from the retrieved context and cites them. It exists so the
end-to-end pipeline — retrieve, ground, answer, judge — runs in CI without an
API key, and so retrieval changes can be attributed to retrieval rather than
to LLM sampling noise. ``LLMGenerator`` swaps in a real model when a key is
present.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from ragproof.retrievers import Retrieved
from ragproof.text import split_sentences, tokenize

ABSTAIN = "I don't have enough information in the provided documents to answer that."


@dataclass
class Answer:
    text: str
    citations: List[str] = field(default_factory=list)
    abstained: bool = False


def format_context(hits: Sequence[Retrieved], max_chars: int = 4000) -> str:
    blocks, used = [], 0
    for hit in hits:
        block = f"[{hit.doc_id}] {hit.title}\n{hit.text}"
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)


class Generator:
    name = "generator"

    def generate(self, question: str, hits: Sequence[Retrieved]) -> Answer:
        raise NotImplementedError  # pragma: no cover - abstract


class ExtractiveGenerator(Generator):
    """Pick the best-supported sentences from context and cite their documents.

    ``abstain_threshold`` is the fraction of the question's content words that
    must appear in the best sentence. Below it the generator refuses to answer.
    Abstention is a measurable behaviour, which is the point: the eval set
    contains questions the corpus cannot answer, and a system that confidently
    answers those is worse than one that says so.
    """

    name = "extractive"

    def __init__(self, max_sentences: int = 2, abstain_threshold: float = 0.25) -> None:
        self.max_sentences = max_sentences
        self.abstain_threshold = abstain_threshold

    def generate(self, question: str, hits: Sequence[Retrieved]) -> Answer:
        q_terms = set(tokenize(question, drop_stopwords=True))
        if not hits or not q_terms:
            return Answer(text=ABSTAIN, citations=[], abstained=True)

        scored = []
        for hit in hits:
            for sent in split_sentences(hit.text):
                terms = set(tokenize(sent, drop_stopwords=True))
                if not terms:
                    continue
                coverage = len(q_terms & terms) / len(q_terms)
                scored.append((coverage, hit.rank, sent, hit.doc_id))

        if not scored:
            return Answer(text=ABSTAIN, citations=[], abstained=True)

        scored.sort(key=lambda x: (-x[0], x[1]))
        if scored[0][0] < self.abstain_threshold:
            return Answer(text=ABSTAIN, citations=[], abstained=True)

        chosen = scored[: self.max_sentences]
        citations: List[str] = []
        parts: List[str] = []
        for coverage, _rank, sent, doc_id in chosen:
            if coverage <= 0:
                continue
            parts.append(f"{sent} [{doc_id}]")
            if doc_id not in citations:
                citations.append(doc_id)
        return Answer(text=" ".join(parts), citations=citations, abstained=False)


class LLMGenerator(Generator):
    """Anthropic or OpenAI backed generator. Requires ``ragproof[llm]`` + an API key."""

    name = "llm"

    PROMPT = (
        "Answer the question using ONLY the documents below. "
        "Cite every claim with the document id in square brackets, e.g. [payments-retry]. "
        "If the documents do not contain the answer, reply exactly: "
        f"{ABSTAIN}\n\nDocuments:\n{{context}}\n\nQuestion: {{question}}\nAnswer:"
    )

    def __init__(
        self,
        provider: str = "anthropic",
        model: str = "claude-sonnet-4-5",
        temperature: float = 0.0,
        max_tokens: int = 400,
    ) -> None:
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, question: str, hits: Sequence[Retrieved]) -> Answer:  # pragma: no cover
        context = format_context(hits)
        prompt = self.PROMPT.format(context=context, question=question)
        text = self._call(prompt)
        cited = [h.doc_id for h in hits if f"[{h.doc_id}]" in text]
        return Answer(text=text, citations=cited, abstained=ABSTAIN[:40] in text)

    def _call(self, prompt: str) -> str:  # pragma: no cover - network path
        if self.provider == "anthropic":
            import anthropic

            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            msg = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(block.text for block in msg.content if block.type == "text")
        if self.provider == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            resp = client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content or ""
        raise ValueError(f"unknown provider: {self.provider}")


_REGISTRY = {"extractive": ExtractiveGenerator, "llm": LLMGenerator}


def build_generator(spec: Optional[dict]) -> Generator:
    spec = dict(spec or {})
    kind = spec.pop("kind", "extractive")
    if kind not in _REGISTRY:
        raise ValueError(f"unknown generator '{kind}' (have: {sorted(_REGISTRY)})")
    return _REGISTRY[kind](**spec)
