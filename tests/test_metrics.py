import math

import pytest

from ragproof import metrics as M


def test_dedupe_preserves_rank_order():
    assert M.dedupe(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_recall_counts_documents_not_chunks():
    # Three chunks of the same document must not inflate recall.
    assert M.recall_at_k(["a", "a", "a"], ["a", "b"], k=3) == 0.5


@pytest.mark.parametrize(
    "retrieved,gold,k,expected",
    [
        (["a", "b", "c"], ["a"], 3, 1.0),
        (["x", "y", "a"], ["a"], 2, 0.0),
        (["a", "b"], ["a", "b"], 2, 1.0),
        ([], ["a"], 5, 0.0),
    ],
)
def test_recall_at_k(retrieved, gold, k, expected):
    assert M.recall_at_k(retrieved, gold, k) == expected


def test_precision_uses_the_truncated_list_as_denominator():
    assert M.precision_at_k(["a", "x"], ["a"], k=5) == 0.5


def test_reciprocal_rank_is_position_sensitive():
    assert M.reciprocal_rank(["x", "a"], ["a"]) == 0.5
    assert M.reciprocal_rank(["a", "x"], ["a"]) == 1.0
    assert M.reciprocal_rank(["x", "y"], ["a"]) == 0.0


def test_ndcg_rewards_higher_placement():
    early = M.ndcg_at_k(["a", "x", "y"], ["a"], k=3)
    late = M.ndcg_at_k(["x", "y", "a"], ["a"], k=3)
    assert early == pytest.approx(1.0)
    assert 0 < late < early


def test_ndcg_is_one_for_a_perfect_ranking():
    assert M.ndcg_at_k(["a", "b", "x"], ["a", "b"], k=3) == pytest.approx(1.0)


def test_hit_rate_is_binary():
    assert M.hit_rate_at_k(["x", "a"], ["a"], 2) == 1.0
    assert M.hit_rate_at_k(["x", "a"], ["a"], 1) == 0.0


def test_token_f1_ignores_stopwords_and_order():
    assert M.token_f1("the payment was held", "payment held") == pytest.approx(1.0)
    assert M.token_f1("completely unrelated text", "payment held") == 0.0


def test_aggregate_means_only_the_keys_present():
    rows = [{"a": 1.0, "b": 0.0}, {"a": 0.0}]
    out = M.aggregate(rows)
    assert out["a"] == 0.5
    assert out["b"] == 0.0
    assert not math.isnan(out["a"])
