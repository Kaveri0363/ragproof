"""End-to-end behaviour: generation, grounding, and abstention."""

import pytest

from ragproof.generation import ABSTAIN, ExtractiveGenerator
from ragproof.judge import OverlapJudge
from ragproof.rerank import LexicalOverlapReranker, build_reranker
from ragproof.retrievers import BM25Retriever, Retrieved


@pytest.fixture
def indexed(tiny_corpus):
    return BM25Retriever().index(tiny_corpus.chunks)


def test_generator_answers_from_context_and_cites(indexed):
    hits = indexed.search("what happens on screening timeout", 3)
    answer = ExtractiveGenerator().generate("what happens on screening timeout", hits)
    assert not answer.abstained
    assert "screening" in answer.citations
    assert "[screening]" in answer.text


def test_generator_abstains_when_context_is_irrelevant(indexed):
    question = "which cloud region hosts the disaster recovery cluster"
    answer = ExtractiveGenerator().generate(question, indexed.search(question, 3))
    assert answer.abstained
    assert answer.text == ABSTAIN
    assert answer.citations == []


def test_generator_abstains_with_no_hits():
    assert ExtractiveGenerator().generate("anything at all", []).abstained


def test_judge_scores_a_copied_sentence_as_grounded():
    context = ["The screening service has a hard timeout of one and a half seconds."]
    verdict = OverlapJudge().score("timeout?", context[0], context, cited=["screening"],
                                   retrieved_doc_ids=["screening"])
    assert verdict.groundedness == pytest.approx(1.0)
    assert verdict.citation_precision == pytest.approx(1.0)
    assert verdict.unsupported_sentences == []


def test_judge_catches_an_invented_claim():
    context = ["The screening service has a hard timeout of one and a half seconds."]
    verdict = OverlapJudge().score(
        "timeout?", "Screening retries forever against a replica in Frankfurt.", context
    )
    assert verdict.groundedness < 0.5
    assert verdict.unsupported_sentences


def test_judge_flags_a_citation_to_a_document_that_was_never_retrieved():
    context = ["Payments are held on a name match."]
    verdict = OverlapJudge().score(
        "why held?", "Payments are held on a name match. [invented-doc]", context,
        cited=["invented-doc"], retrieved_doc_ids=["screening"],
    )
    assert verdict.citation_precision == 0.0


def _hit(doc_id, rank, text):
    return Retrieved(chunk_id=f"{doc_id}::0", doc_id=doc_id, score=1.0 / rank,
                     rank=rank, text=text, title=doc_id)


def test_reranker_promotes_the_better_candidate():
    hits = [
        _hit("noise", 1, "Unrelated text about connection pools and Hikari settings."),
        _hit("gold", 2, "The screening service has a hard timeout of one and a half seconds."),
    ]
    out = LexicalOverlapReranker().rerank("screening service hard timeout", hits, k=2)
    assert out[0].doc_id == "gold"
    assert out[0].rank == 1


def test_reranker_keeps_first_stage_order_when_nothing_matches():
    hits = [_hit("a", 1, "alpha beta"), _hit("b", 2, "gamma delta")]
    out = LexicalOverlapReranker().rerank("zzzz qqqq", hits, k=2)
    assert [h.doc_id for h in out] == ["a", "b"]


def test_noop_reranker_is_a_pure_truncation():
    hits = [_hit("a", 1, "x"), _hit("b", 2, "y"), _hit("c", 3, "z")]
    out = build_reranker({"kind": "none"}).rerank("q", hits, k=2)
    assert [h.doc_id for h in out] == ["a", "b"]
