"""The harness has to be trustworthy before its numbers are."""

import json
import os

import pytest

from ragproof.cli import main
from ragproof.config import load_config
from ragproof.dataset import Example, load_examples, validate_examples
from ragproof.report import compare, html_report, markdown_report
from ragproof.runner import run_experiment


@pytest.fixture(scope="module")
def config():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return load_config(os.path.join(root, "configs", "default.yaml"))


@pytest.fixture(scope="module")
def result(config):
    return run_experiment(config)


def test_the_bundled_eval_set_is_valid(config):
    from ragproof.corpus import load_corpus

    corpus = load_corpus(config.corpus)
    problems = validate_examples(
        load_examples(config.dataset), known_doc_ids={d.doc_id for d in corpus.documents}
    )
    assert problems == []


def test_validator_catches_a_gold_document_that_does_not_exist():
    bad = [Example(qid="q1", question="?", gold_doc_ids=["ghost"])]
    assert any("ghost" in p for p in validate_examples(bad, known_doc_ids={"real"}))


def test_validator_catches_duplicate_ids_and_missing_labels():
    rows = [
        Example(qid="q1", question="a", gold_doc_ids=["d"]),
        Example(qid="q1", question="b", gold_doc_ids=[]),
    ]
    problems = validate_examples(rows)
    assert any("duplicate" in p for p in problems)
    assert any("no gold documents" in p for p in problems)


def test_experiment_scores_every_system_and_question(result, config):
    assert len(result.systems) == len(config.systems)
    for system in result.systems:
        assert len(system.per_question) == result.dataset_size
        assert 0.0 <= system.metrics["recall_at_k"] <= 1.0
        assert system.metrics["questions"] == result.dataset_size


def test_experiment_is_reproducible(config):
    a = run_experiment(config).systems[0].metrics
    b = run_experiment(config).systems[0].metrics
    for key in a:
        if key == "latency_ms":
            continue  # wall clock, not a property of the pipeline
        assert a[key] == b[key], f"{key} is not reproducible"


def test_unanswerable_questions_are_scored_on_abstention_only(result):
    system = result.systems[0]
    negatives = [q for q in system.per_question if not q.answerable]
    assert negatives, "the eval set must contain unanswerable questions"
    for row in negatives:
        assert "recall_at_k" not in row.scores
        assert "abstain_accuracy" in row.scores


def test_answer_quality_is_only_scored_on_answers_that_were_given(result):
    for system in result.systems:
        for row in system.per_question:
            if row.abstained:
                assert "groundedness" not in row.scores
            elif row.answerable:
                assert "groundedness" in row.scores


def test_baseline_beats_a_deliberately_bad_configuration(config):
    """A harness that cannot rank a good pipeline above a bad one is useless."""
    import copy

    broken = copy.deepcopy(config)
    broken.systems = [s for s in broken.systems if s.name == "bm25-baseline"]
    crippled = copy.deepcopy(broken.systems[0])
    crippled.name = "crippled"
    crippled.chunking = {"strategy": "fixed", "size": 8, "overlap": 0}
    broken.systems.append(crippled)

    scores = {s.name: s.metrics["recall_at_k"] for s in run_experiment(broken).systems}
    assert scores["bm25-baseline"] > scores["crippled"]


def test_reports_render(result):
    md = markdown_report(result)
    assert "## Leaderboard" in md and "Recall@k" in md
    assert result.systems[0].name in md
    html = html_report(result)
    assert html.startswith("<!doctype html>") and "</html>" in html
    assert "prefers-color-scheme" in html


def test_compare_detects_a_regression_beyond_tolerance():
    base = {"systems": [{"name": "s", "metrics": {"recall_at_k": 0.90, "mrr": 0.80}}]}
    now = {"systems": [{"name": "s", "metrics": {"recall_at_k": 0.70, "mrr": 0.81}}]}
    regressions = compare(now, base, tolerance=0.01)
    assert len(regressions) == 1
    assert regressions[0]["metric"] == "recall_at_k"
    assert regressions[0]["delta"] == pytest.approx(-0.20)


def test_compare_ignores_noise_within_tolerance():
    base = {"systems": [{"name": "s", "metrics": {"recall_at_k": 0.90}}]}
    now = {"systems": [{"name": "s", "metrics": {"recall_at_k": 0.895}}]}
    assert compare(now, base, tolerance=0.01) == []


def test_compare_ignores_systems_absent_from_the_baseline():
    base = {"systems": [{"name": "old", "metrics": {"recall_at_k": 0.9}}]}
    now = {"systems": [{"name": "new", "metrics": {"recall_at_k": 0.1}}]}
    assert compare(now, base, tolerance=0.01) == []


def test_cli_eval_and_check_round_trip(tmp_path, config):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = os.path.join(root, "configs", "default.yaml")
    out = tmp_path / "out"
    assert main(["eval", "--config", cfg, "--out-dir", str(out)]) == 0

    produced = out / "default.json"
    assert produced.is_file()
    payload = json.loads(produced.read_text())
    assert payload["systems"] and payload["systems"][0]["per_question"]

    assert main(["check", "--results", str(produced), "--baseline", str(produced)]) == 0

    degraded = json.loads(produced.read_text())
    for system in degraded["systems"]:
        system["metrics"]["recall_at_k"] = 0.0
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(degraded))
    # current results are *better* than this baseline, so still no regression
    assert main(["check", "--results", str(produced), "--baseline", str(baseline)]) == 0
    # and the reverse direction must fail
    assert main(["check", "--results", str(baseline), "--baseline", str(produced)]) == 1


def test_cli_lint_and_ask(capsys):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = os.path.join(root, "configs", "default.yaml")
    assert main(["lint", "--config", cfg]) == 0
    assert main(["ask", "what is the TARGET2 cut-off?", "--config", cfg]) == 0
    assert "settlement-cutoffs" in capsys.readouterr().out


def test_cli_reports_a_missing_config_cleanly():
    assert main(["lint", "--config", "does/not/exist.yaml"]) == 2
