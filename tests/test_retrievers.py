import pytest

from ragproof.retrievers import BM25Retriever, DenseRetriever, HybridRetriever, build_retriever


def _ids(hits):
    return [h.doc_id for h in hits]


def test_bm25_finds_the_right_document(tiny_corpus):
    r = BM25Retriever().index(tiny_corpus.chunks)
    assert _ids(r.search("how many attempts before the dead letter queue", 1)) == ["retry"]
    assert _ids(r.search("screening hard timeout fails closed", 1)) == ["screening"]
    assert _ids(r.search("TARGET2 cut-off for customer payments", 1)) == ["cutoffs"]


def test_bm25_ranks_by_relevance_not_document_order(tiny_corpus):
    r = BM25Retriever().index(tiny_corpus.chunks)
    hits = r.search("sanctions screening timeout", 3)
    assert hits[0].doc_id == "screening"
    assert hits[0].score > hits[-1].score


def test_bm25_matches_a_title_only_term(tiny_corpus):
    # 'sanctions' appears in the document title, not in the chunk body.
    r = BM25Retriever().index(tiny_corpus.chunks)
    assert _ids(r.search("sanctions", 1)) == ["screening"]


def test_dense_retrieval_is_deterministic(tiny_corpus):
    a = DenseRetriever().index(tiny_corpus.chunks).search("exponential backoff", 3)
    b = DenseRetriever().index(tiny_corpus.chunks).search("exponential backoff", 3)
    assert [(h.chunk_id, round(h.score, 6)) for h in a] == [
        (h.chunk_id, round(h.score, 6)) for h in b
    ], "the hashing embedder must be reproducible across instances"


def test_dense_retrieval_finds_the_right_document(tiny_corpus):
    r = DenseRetriever().index(tiny_corpus.chunks)
    assert _ids(r.search("retry backoff delay multiplier", 1)) == ["retry"]


def test_search_before_index_raises(tiny_corpus):
    with pytest.raises(RuntimeError):
        DenseRetriever().search("anything", 3)


def test_hybrid_fuses_both_members(tiny_corpus):
    hybrid = HybridRetriever().index(tiny_corpus.chunks)
    hits = hybrid.search("payment held on hold screening", 3)
    assert hits[0].doc_id == "screening"
    assert all(hits[i].score >= hits[i + 1].score for i in range(len(hits) - 1))


def test_k_is_respected_and_ranks_are_contiguous(tiny_corpus):
    for retriever in (BM25Retriever(), DenseRetriever(), HybridRetriever()):
        hits = retriever.index(tiny_corpus.chunks).search("payment", 2)
        assert len(hits) <= 2
        assert [h.rank for h in hits] == list(range(1, len(hits) + 1))


def test_unknown_retriever_kind_is_rejected():
    with pytest.raises(ValueError, match="unknown retriever"):
        build_retriever({"kind": "vector-magic"})
