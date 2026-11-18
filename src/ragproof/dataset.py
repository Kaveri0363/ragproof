"""Labelled evaluation examples."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Example:
    qid: str
    question: str
    gold_doc_ids: List[str] = field(default_factory=list)
    reference_answer: str = ""
    category: str = "general"
    answerable: bool = True

    @property
    def is_negative(self) -> bool:
        """True for questions the corpus deliberately cannot answer."""
        return not self.answerable or not self.gold_doc_ids


def load_examples(path: str) -> List[Example]:
    """Load a JSONL evaluation set."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"evaluation set not found: {path}")
    out: List[Example] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON — {exc}") from exc
            out.append(
                Example(
                    qid=row.get("qid") or f"q{line_no:03d}",
                    question=row["question"],
                    gold_doc_ids=list(row.get("gold_doc_ids", [])),
                    reference_answer=row.get("reference_answer", ""),
                    category=row.get("category", "general"),
                    answerable=bool(row.get("answerable", True)),
                )
            )
    if not out:
        raise ValueError(f"no examples found in {path}")
    return out


def validate_examples(examples: List[Example], known_doc_ids: Optional[set] = None) -> List[str]:
    """Return a list of dataset problems. An eval set is code: it needs a linter."""
    problems: List[str] = []
    seen = set()
    for ex in examples:
        if ex.qid in seen:
            problems.append(f"duplicate qid: {ex.qid}")
        seen.add(ex.qid)
        if not ex.question.strip():
            problems.append(f"{ex.qid}: empty question")
        if ex.answerable and not ex.gold_doc_ids:
            problems.append(f"{ex.qid}: marked answerable but has no gold documents")
        if known_doc_ids is not None:
            for doc_id in ex.gold_doc_ids:
                if doc_id not in known_doc_ids:
                    problems.append(f"{ex.qid}: gold document '{doc_id}' is not in the corpus")
    return problems
