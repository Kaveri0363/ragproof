"""ragproof — an offline, reproducible evaluation harness for RAG pipelines."""

__version__ = "0.1.0"

from ragproof.corpus import Chunk, Document, load_corpus
from ragproof.dataset import Example, load_examples
from ragproof.runner import SystemResult, run_experiment

__all__ = [
    "Chunk",
    "Document",
    "Example",
    "SystemResult",
    "load_corpus",
    "load_examples",
    "run_experiment",
    "__version__",
]
