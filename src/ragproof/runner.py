"""The experiment runner: build each pipeline variant, score it, compare."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Sequence

from ragproof import metrics as M
from ragproof.config import ExperimentConfig, SystemConfig
from ragproof.corpus import build_chunks, corpus_stats, load_corpus
from ragproof.dataset import Example, load_examples, validate_examples
from ragproof.generation import build_generator
from ragproof.judge import build_judge
from ragproof.rerank import build_reranker
from ragproof.retrievers import build_retriever


@dataclass
class QuestionResult:
    qid: str
    question: str
    category: str
    answerable: bool
    gold_doc_ids: List[str]
    retrieved_doc_ids: List[str]
    answer: str
    abstained: bool
    latency_ms: float
    scores: Dict[str, float] = field(default_factory=dict)
    unsupported_sentences: List[str] = field(default_factory=list)


@dataclass
class SystemResult:
    name: str
    config: Dict[str, Any]
    metrics: Dict[str, float]
    per_question: List[QuestionResult]
    index_ms: float
    chunk_stats: Dict[str, float]
    by_category: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "config": self.config,
            "metrics": self.metrics,
            "by_category": self.by_category,
            "index_ms": round(self.index_ms, 2),
            "chunk_stats": self.chunk_stats,
            "per_question": [asdict(q) for q in self.per_question],
        }


@dataclass
class ExperimentResult:
    name: str
    k: int
    dataset_size: int
    corpus_size: int
    systems: List[SystemResult]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "k": self.k,
            "dataset_size": self.dataset_size,
            "corpus_size": self.corpus_size,
            "systems": [s.as_dict() for s in self.systems],
        }

    def leaderboard(self, key: str = "recall_at_k") -> List[SystemResult]:
        return sorted(self.systems, key=lambda s: -s.metrics.get(key, 0.0))


def evaluate_system(
    system: SystemConfig,
    corpus,
    examples: Sequence[Example],
    k: int,
    retrieval_depth: int,
) -> SystemResult:
    chunked = build_chunks(corpus, **system.chunking)

    retriever = build_retriever(system.retriever)
    reranker = build_reranker(system.reranker)
    generator = build_generator(system.generator)
    judge = build_judge(system.judge)

    t0 = time.perf_counter()
    retriever.index(chunked.chunks)
    index_ms = (time.perf_counter() - t0) * 1000

    depth = max(retrieval_depth, k)
    rows: List[Dict[str, float]] = []
    per_question: List[QuestionResult] = []

    for ex in examples:
        t1 = time.perf_counter()
        candidates = retriever.search(ex.question, depth)
        hits = reranker.rerank(ex.question, candidates, k)
        answer = generator.generate(ex.question, hits)
        latency_ms = (time.perf_counter() - t1) * 1000

        retrieved_docs = M.dedupe([h.doc_id for h in hits])
        contexts = [h.text for h in hits]
        verdict = judge.score(
            ex.question,
            answer.text,
            contexts,
            cited=answer.citations,
            retrieved_doc_ids=[h.doc_id for h in hits],
        )

        scores: Dict[str, float] = {"latency_ms": round(latency_ms, 3)}
        if ex.is_negative:
            # For unanswerable questions the only thing that matters is whether
            # the system refused. Answering is a hallucination, by construction.
            scores["abstain_accuracy"] = 1.0 if answer.abstained else 0.0
        else:
            scores.update(
                {
                    "recall_at_k": M.recall_at_k(retrieved_docs, ex.gold_doc_ids, k),
                    "precision_at_k": M.precision_at_k(retrieved_docs, ex.gold_doc_ids, k),
                    "hit_rate_at_k": M.hit_rate_at_k(retrieved_docs, ex.gold_doc_ids, k),
                    "mrr": M.reciprocal_rank(retrieved_docs, ex.gold_doc_ids),
                    "ndcg_at_k": M.ndcg_at_k(retrieved_docs, ex.gold_doc_ids, k),
                    "answer_rate": 0.0 if answer.abstained else 1.0,
                }
            )
            if not answer.abstained:
                # Groundedness and citation precision are only meaningful for
                # answers the system actually gave. Folding abstentions in at
                # 0.0 would conflate "refused to answer" with "made something
                # up", which are opposite failures needing opposite fixes.
                scores["groundedness"] = verdict.groundedness
                scores["citation_precision"] = verdict.citation_precision
                if ex.reference_answer:
                    scores["answer_f1"] = M.token_f1(answer.text, ex.reference_answer)
        scores = {key: round(float(val), 4) for key, val in scores.items()}
        rows.append(scores)
        per_question.append(
            QuestionResult(
                qid=ex.qid,
                question=ex.question,
                category=ex.category,
                answerable=not ex.is_negative,
                gold_doc_ids=list(ex.gold_doc_ids),
                retrieved_doc_ids=retrieved_docs,
                answer=answer.text,
                abstained=answer.abstained,
                latency_ms=round(latency_ms, 3),
                scores=scores,
                # An abstention asserts nothing, so it has nothing unsupported.
                unsupported_sentences=[] if answer.abstained else verdict.unsupported_sentences,
            )
        )

    aggregated = M.aggregate(rows)
    aggregated["questions"] = len(examples)

    # Aggregate scores split by question category. A single mean hides the
    # thing worth knowing: sparse retrieval wins on exact-term lookups while
    # dense retrieval earns its keep on paraphrased questions, and an averaged
    # leaderboard row shows neither.
    by_category: Dict[str, Dict[str, float]] = {}
    for category in sorted({ex.category for ex in examples}):
        cat_rows = [
            q.scores for q, ex in zip(per_question, examples) if ex.category == category
        ]
        stats = M.aggregate(cat_rows)
        stats["questions"] = len(cat_rows)
        by_category[category] = stats

    return SystemResult(
        name=system.name,
        config=system.as_dict(),
        metrics=aggregated,
        per_question=per_question,
        index_ms=index_ms,
        chunk_stats=corpus_stats(chunked),
        by_category=by_category,
    )


def run_experiment(config: ExperimentConfig, *, strict: bool = True) -> ExperimentResult:
    corpus = load_corpus(config.corpus)
    examples = load_examples(config.dataset)

    problems = validate_examples(examples, known_doc_ids={d.doc_id for d in corpus.documents})
    if problems and strict:
        raise ValueError("evaluation set is invalid:\n  - " + "\n  - ".join(problems))

    results = [
        evaluate_system(system, corpus, examples, config.k, config.retrieval_depth)
        for system in config.systems
    ]
    return ExperimentResult(
        name=config.name,
        k=config.k,
        dataset_size=len(examples),
        corpus_size=len(corpus.documents),
        systems=results,
    )
