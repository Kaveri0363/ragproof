"""Experiment configuration.

An experiment is data, not code: a YAML file naming the corpus, the labelled
set, and the list of pipeline variants to compare. That is what makes a sweep
reproducible by anyone who clones the repo.
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

import yaml

DEFAULT_SYSTEM: Dict[str, Any] = {
    "chunking": {"strategy": "sentence", "size": 120, "overlap": 30},
    "retriever": {"kind": "bm25"},
    "reranker": {"kind": "none"},
    "generator": {"kind": "extractive"},
    "judge": {"kind": "overlap"},
}


@dataclass
class SystemConfig:
    name: str
    chunking: Dict[str, Any] = field(default_factory=dict)
    retriever: Dict[str, Any] = field(default_factory=dict)
    reranker: Dict[str, Any] = field(default_factory=dict)
    generator: Dict[str, Any] = field(default_factory=dict)
    judge: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "chunking": self.chunking,
            "retriever": self.retriever,
            "reranker": self.reranker,
            "generator": self.generator,
            "judge": self.judge,
            "notes": self.notes,
        }


@dataclass
class ExperimentConfig:
    name: str
    corpus: str
    dataset: str
    k: int = 5
    retrieval_depth: int = 20
    systems: List[SystemConfig] = field(default_factory=list)
    source_path: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "corpus": self.corpus,
            "dataset": self.dataset,
            "k": self.k,
            "retrieval_depth": self.retrieval_depth,
            "systems": [s.as_dict() for s in self.systems],
        }


def _merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: str) -> ExperimentConfig:
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    base_dir = os.path.dirname(os.path.abspath(path))

    def resolve(p: str) -> str:
        return p if os.path.isabs(p) else os.path.normpath(os.path.join(base_dir, p))

    defaults = _merge(DEFAULT_SYSTEM, raw.get("defaults", {}))
    systems: List[SystemConfig] = []
    for i, entry in enumerate(raw.get("systems") or [{}]):
        entry = dict(entry)
        name = entry.pop("name", f"system-{i + 1}")
        notes = entry.pop("notes", "")
        merged = _merge(defaults, entry)
        systems.append(
            SystemConfig(
                name=name,
                chunking=merged["chunking"],
                retriever=merged["retriever"],
                reranker=merged["reranker"],
                generator=merged["generator"],
                judge=merged["judge"],
                notes=notes,
            )
        )

    names = [s.name for s in systems]
    if len(set(names)) != len(names):
        raise ValueError(f"system names must be unique, got: {names}")

    return ExperimentConfig(
        name=raw.get("name", os.path.splitext(os.path.basename(path))[0]),
        corpus=resolve(raw.get("corpus", "data/corpus")),
        dataset=resolve(raw.get("dataset", "data/qa.jsonl")),
        k=int(raw.get("k", 5)),
        retrieval_depth=int(raw.get("retrieval_depth", 20)),
        systems=systems,
        source_path=os.path.abspath(path),
    )
