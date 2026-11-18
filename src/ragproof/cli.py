"""Command line interface.

    ragproof eval    --config configs/default.yaml
    ragproof check   --results results/latest.json --baseline results/baseline.json
    ragproof lint    --config configs/default.yaml
    ragproof ask     "why did pacs.008 fail validation?"
    ragproof explain --results results/latest.json --system hybrid+rerank --qid q014
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from ragproof import __version__
from ragproof.config import load_config
from ragproof.corpus import build_chunks, load_corpus
from ragproof.dataset import load_examples, validate_examples
from ragproof.generation import build_generator
from ragproof.rerank import build_reranker
from ragproof.report import compare, html_report, markdown_report, write_json
from ragproof.retrievers import build_retriever
from ragproof.runner import run_experiment

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def _color(text: str, code: str) -> str:
    return text if os.environ.get("NO_COLOR") else f"{code}{text}{RESET}"


def cmd_eval(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    print(_color(f"▸ {config.name}", DIM) + f"  {len(config.systems)} system(s), k={config.k}")
    result = run_experiment(config, strict=not args.no_strict)

    os.makedirs(args.out_dir, exist_ok=True)
    json_path = os.path.join(args.out_dir, f"{config.name}.json")
    md_path = os.path.join(args.out_dir, f"{config.name}.md")
    html_path = os.path.join(args.out_dir, f"{config.name}.html")

    write_json(result, json_path)
    markdown = markdown_report(result, sort_key=args.sort_key)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(markdown + "\n")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html_report(result, sort_key=args.sort_key))

    print()
    print(markdown.split("## Configurations")[0].strip())
    print()
    print(_color(f"✓ wrote {json_path}, {md_path}, {html_path}", GREEN))

    if args.baseline and os.path.isfile(args.baseline):
        return _report_regressions(json_path, args.baseline, args.tolerance)
    return 0


def _report_regressions(results_path: str, baseline_path: str, tolerance: float) -> int:
    with open(results_path, encoding="utf-8") as fh:
        current = json.load(fh)
    with open(baseline_path, encoding="utf-8") as fh:
        baseline = json.load(fh)
    regressions = compare(current, baseline, tolerance=tolerance)
    if not regressions:
        print(_color(f"✓ no regression vs baseline (tolerance {tolerance})", GREEN))
        return 0
    print(_color(f"✗ {len(regressions)} regression(s) vs baseline:", RED))
    for reg in regressions:
        print(
            f"    {reg['system']}: {reg['metric']} "
            f"{reg['baseline']:.3f} → {reg['current']:.3f} ({reg['delta']:+.3f})"
        )
    return 1


def cmd_check(args: argparse.Namespace) -> int:
    return _report_regressions(args.results, args.baseline, args.tolerance)


def cmd_lint(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    corpus = load_corpus(config.corpus)
    examples = load_examples(config.dataset)
    problems = validate_examples(examples, known_doc_ids={d.doc_id for d in corpus.documents})
    print(f"corpus:  {len(corpus.documents)} documents from {config.corpus}")
    negatives = sum(1 for e in examples if e.is_negative)
    print(f"dataset: {len(examples)} questions ({negatives} unanswerable) "
          f"from {config.dataset}")
    if problems:
        print(_color(f"✗ {len(problems)} problem(s):", RED))
        for problem in problems:
            print(f"    {problem}")
        return 1
    print(_color("✓ evaluation set is well-formed", GREEN))
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    system = next((s for s in config.systems if s.name == args.system), config.systems[0])
    corpus = build_chunks(load_corpus(config.corpus), **system.chunking)
    retriever = build_retriever(system.retriever).index(corpus.chunks)
    reranker = build_reranker(system.reranker)
    generator = build_generator(system.generator)

    candidates = retriever.search(args.question, config.retrieval_depth)
    hits = reranker.rerank(args.question, candidates, args.k)
    answer = generator.generate(args.question, hits)

    print(_color(f"system: {system.name}", DIM))
    print()
    print(_color("answer:", YELLOW), answer.text)
    print()
    print(_color("retrieved:", DIM))
    for hit in hits:
        snippet = hit.text[:110].replace("\n", " ")
        print(f"  {hit.rank}. [{hit.doc_id}] {hit.score:.4f}  {snippet}…")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    with open(args.results, encoding="utf-8") as fh:
        data = json.load(fh)
    systems = data["systems"]
    system = next((s for s in systems if s["name"] == args.system), systems[0])
    row = next((q for q in system["per_question"] if q["qid"] == args.qid), None)
    if row is None:
        print(_color(f"no question '{args.qid}' in system '{system['name']}'", RED))
        return 1
    print(f"{system['name']} · {row['qid']}")
    print(f"  question : {row['question']}")
    print(f"  gold     : {', '.join(row['gold_doc_ids']) or '(none — unanswerable)'}")
    print(f"  retrieved: {', '.join(row['retrieved_doc_ids'])}")
    print(f"  answer   : {row['answer']}")
    if row["unsupported_sentences"]:
        print(_color("  unsupported:", RED))
        for sent in row["unsupported_sentences"]:
            print(f"    - {sent}")
    print("  scores   : " + ", ".join(f"{k}={v}" for k, v in sorted(row["scores"].items())))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ragproof", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"ragproof {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_eval = sub.add_parser("eval", help="run an experiment and write reports")
    p_eval.add_argument("--config", default="configs/default.yaml")
    p_eval.add_argument("--out-dir", default="results")
    p_eval.add_argument("--baseline", default=None, help="compare against this results JSON")
    p_eval.add_argument("--tolerance", type=float, default=0.01)
    p_eval.add_argument("--sort-key", default="recall_at_k")
    p_eval.add_argument(
        "--no-strict", action="store_true", help="warn instead of failing on a bad eval set"
    )
    p_eval.set_defaults(func=cmd_eval)

    p_check = sub.add_parser("check", help="fail if results regressed against a baseline")
    p_check.add_argument("--results", required=True)
    p_check.add_argument("--baseline", required=True)
    p_check.add_argument("--tolerance", type=float, default=0.01)
    p_check.set_defaults(func=cmd_check)

    p_lint = sub.add_parser("lint", help="validate the corpus and labelled set")
    p_lint.add_argument("--config", default="configs/default.yaml")
    p_lint.set_defaults(func=cmd_lint)

    p_ask = sub.add_parser("ask", help="run one question through a pipeline")
    p_ask.add_argument("question")
    p_ask.add_argument("--config", default="configs/default.yaml")
    p_ask.add_argument("--system", default=None)
    p_ask.add_argument("-k", type=int, default=5)
    p_ask.set_defaults(func=cmd_ask)

    p_exp = sub.add_parser("explain", help="show why one question scored the way it did")
    p_exp.add_argument("--results", required=True)
    p_exp.add_argument("--system", default=None)
    p_exp.add_argument("--qid", required=True)
    p_exp.set_defaults(func=cmd_explain)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (FileNotFoundError, ValueError) as exc:
        print(_color(f"error: {exc}", RED), file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
