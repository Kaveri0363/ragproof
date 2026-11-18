"""Reporting: a leaderboard humans read, and a diff CI reads."""

from __future__ import annotations

import datetime as _dt
import html
import json
from typing import Any, Dict, List, Optional, Sequence

HEADLINE = [
    "recall_at_k",
    "mrr",
    "ndcg_at_k",
    "precision_at_k",
    "groundedness",
    "citation_precision",
    "answer_f1",
    "abstain_accuracy",
    "answer_rate",
    "latency_ms",
]

PRETTY = {
    "recall_at_k": "Recall@k",
    "precision_at_k": "Precision@k",
    "hit_rate_at_k": "Hit@k",
    "mrr": "MRR",
    "ndcg_at_k": "nDCG@k",
    "answer_f1": "Answer F1",
    "groundedness": "Grounded",
    "citation_precision": "Cite prec.",
    "abstain_accuracy": "Abstain acc.",
    "answer_rate": "Answer rate",
    "latency_ms": "Latency (ms)",
}


def _fmt(value: Optional[float], key: str) -> str:
    if value is None:
        return "—"
    if key == "latency_ms":
        return f"{value:.1f}"
    return f"{value:.3f}"


def _describe(config: Dict[str, Any]) -> str:
    chunk = config.get("chunking", {})
    parts = [
        config.get("retriever", {}).get("kind", "?"),
        f"chunk {chunk.get('size', '?')}/{chunk.get('overlap', '?')} {chunk.get('strategy', '')}",
    ]
    rerank = config.get("reranker", {}).get("kind", "none")
    if rerank != "none":
        parts.append(f"rerank:{rerank}")
    return ", ".join(p for p in parts if p)


def markdown_report(result, sort_key: str = "recall_at_k") -> str:
    systems = sorted(result.systems, key=lambda s: -s.metrics.get(sort_key, 0.0))
    keys = [k for k in HEADLINE if any(k in s.metrics for s in systems)]

    lines: List[str] = []
    lines.append(f"# ragproof — `{result.name}`")
    lines.append("")
    lines.append(
        f"_{result.corpus_size} documents · {result.dataset_size} labelled questions · "
        f"k={result.k} · "
        f"generated {_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"
    )
    lines.append("")
    lines.append("## Leaderboard")
    lines.append("")
    header = "| System | " + " | ".join(PRETTY.get(k, k) for k in keys) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(keys) + 1))
    for s in systems:
        cells = [_fmt(s.metrics.get(k), k) for k in keys]
        lines.append(f"| `{s.name}` | " + " | ".join(cells) + " |")
    lines.append("")

    best = systems[0]
    worst = systems[-1]
    if len(systems) > 1 and worst.metrics.get(sort_key) is not None:
        delta = best.metrics.get(sort_key, 0) - worst.metrics.get(sort_key, 0)
        metric_name = PRETTY.get(sort_key, sort_key)
        lines.append(
            f"**`{best.name}` leads `{worst.name}` by {delta:+.3f} {metric_name}.**"
        )
        lines.append("")

    lines.append("## Configurations")
    lines.append("")
    for s in systems:
        notes = f" · {s.config['notes']}" if s.config.get("notes") else ""
        lines.append(
            f"- `{s.name}` — {_describe(s.config)} · {s.chunk_stats['chunks']} chunks · "
            f"index {s.index_ms:.0f} ms{notes}"
        )
    lines.append("")

    categories = sorted({c for s in systems for c in s.by_category})
    scored_cats = [
        c for c in categories
        if any("recall_at_k" in s.by_category.get(c, {}) for s in systems)
    ]
    if scored_cats:
        lines.append("## Recall@k by question type")
        lines.append("")
        heads = [f"{c} ({systems[0].by_category[c]['questions']})" for c in scored_cats]
        lines.append("| System | " + " | ".join(heads) + " |")
        lines.append("|" + "---|" * (len(scored_cats) + 1))
        for s in systems:
            cells = [
                _fmt(s.by_category.get(c, {}).get("recall_at_k"), "recall_at_k")
                for c in scored_cats
            ]
            lines.append(f"| `{s.name}` | " + " | ".join(cells) + " |")
        lines.append("")

    lines.append("## Hardest questions")
    lines.append("")
    lines.append("Questions the leading system failed to retrieve any gold document for:")
    lines.append("")
    failures = [
        q for q in best.per_question if q.answerable and q.scores.get("recall_at_k", 0) == 0
    ]
    if failures:
        for q in failures[:10]:
            got = ", ".join(q.retrieved_doc_ids[:3])
            lines.append(
                f"- `{q.qid}` — {q.question}  \n"
                f"  gold: `{', '.join(q.gold_doc_ids)}` · got: `{got}`"
            )
    else:
        lines.append(
            "- _None — the leading system retrieved a gold document for every question._"
        )
    lines.append("")
    return "\n".join(lines)


def html_report(result, sort_key: str = "recall_at_k") -> str:
    systems = sorted(result.systems, key=lambda s: -s.metrics.get(sort_key, 0.0))
    keys = [k for k in HEADLINE if any(k in s.metrics for s in systems)]
    best_by_key = {
        k: max((s.metrics.get(k, 0.0) for s in systems), default=0.0)
        for k in keys
        if k != "latency_ms"
    }

    rows = []
    for s in systems:
        cells = []
        for k in keys:
            val = s.metrics.get(k)
            top = k in best_by_key and val is not None and abs(val - best_by_key[k]) < 1e-9
            cells.append(
                f'<td class="num{" best" if top else ""}">{_fmt(val, k)}</td>'
            )
        rows.append(
            f'<tr><th scope="row"><code>{html.escape(s.name)}</code>'
            f'<span class="cfg">{html.escape(_describe(s.config))}</span></th>'
            + "".join(cells)
            + "</tr>"
        )

    head = "".join(f"<th>{html.escape(PRETTY.get(k, k))}</th>" for k in keys)
    generated = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ragproof — {html.escape(result.name)}</title>
<style>
  :root {{ color-scheme: light dark; --bg:#fbfbfa; --fg:#1a1a18; --mut:#6b6b66;
           --line:#e3e3df; --card:#fff; --best:#0b6b53; --bestbg:#e6f4ef; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#141413; --fg:#f0efec; --mut:#9a9a94; --line:#2b2b28; --card:#1c1c1a;
             --best:#6ee7b7; --bestbg:#10322a; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:2.5rem 1.25rem; background:var(--bg); color:var(--fg);
          font:16px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Inter,sans-serif; }}
  main {{ max-width:1040px; margin:0 auto; }}
  h1 {{ font-size:1.6rem; margin:0 0 .25rem; letter-spacing:-.02em; }}
  .meta {{ color:var(--mut); font-size:.85rem; margin-bottom:2rem; }}
  .wrap {{ overflow-x:auto; background:var(--card); border:1px solid var(--line);
           border-radius:12px; }}
  table {{ border-collapse:collapse; width:100%; font-size:.9rem; }}
  th,td {{ padding:.7rem .9rem; text-align:left; border-bottom:1px solid var(--line);
           white-space:nowrap; }}
  thead th {{ font-size:.72rem; text-transform:uppercase; letter-spacing:.06em;
              color:var(--mut); font-weight:600; }}
  tbody tr:last-child th, tbody tr:last-child td {{ border-bottom:none; }}
  td.num {{ font-variant-numeric:tabular-nums; text-align:right; }}
  td.best {{ color:var(--best); background:var(--bestbg); font-weight:600; }}
  th[scope=row] {{ font-weight:600; }}
  .cfg {{ display:block; font-weight:400; font-size:.75rem; color:var(--mut); }}
  code {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.85em; }}
</style></head>
<body><main>
  <h1>ragproof — {html.escape(result.name)}</h1>
  <p class="meta">{result.corpus_size} documents · {result.dataset_size} labelled questions ·
     k={result.k} · generated {generated}</p>
  <div class="wrap"><table>
    <thead><tr><th>System</th>{head}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</main></body></html>"""


def compare(
    current: Dict[str, Any],
    baseline: Dict[str, Any],
    *,
    tolerance: float = 0.01,
    watch: Sequence[str] = ("recall_at_k", "mrr", "groundedness", "abstain_accuracy"),
) -> List[Dict[str, Any]]:
    """Return metric regressions worse than *tolerance*.

    This is the function the CI gate calls. A RAG pipeline has no compiler:
    a chunk-size tweak that quietly drops recall by 8% looks exactly like a
    successful commit unless something checks.
    """
    base_by_name = {s["name"]: s for s in baseline.get("systems", [])}
    regressions: List[Dict[str, Any]] = []
    for system in current.get("systems", []):
        base = base_by_name.get(system["name"])
        if base is None:
            continue
        for key in watch:
            if key not in system["metrics"] or key not in base["metrics"]:
                continue
            now, then = system["metrics"][key], base["metrics"][key]
            if now < then - tolerance:
                regressions.append(
                    {
                        "system": system["name"],
                        "metric": key,
                        "baseline": then,
                        "current": now,
                        "delta": round(now - then, 4),
                    }
                )
    return regressions


def write_json(result, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result.as_dict(), fh, indent=2, sort_keys=False)
        fh.write("\n")
