import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from ragproof.corpus import Corpus, Document, build_chunks  # noqa: E402


@pytest.fixture
def repo_root():
    return ROOT


@pytest.fixture
def tiny_corpus():
    docs = [
        Document(
            doc_id="retry",
            title="Payment Retry Policy",
            text=(
                "Transient failures are retried with exponential backoff. "
                "The base delay is two seconds and the multiplier is three. "
                "After five attempts the payment moves to the dead letter queue. "
                "Business rejections are never retried."
            ),
        ),
        Document(
            doc_id="screening",
            title="Sanctions Screening Holds",
            text=(
                "A name match above the similarity threshold places the payment on hold. "
                "The screening service has a hard timeout of one and a half seconds. "
                "On timeout the payment fails closed and is held rather than allowed through."
            ),
        ),
        Document(
            doc_id="cutoffs",
            title="Settlement Cut-off Times",
            text=(
                "For TARGET2 the cut-off is 17:00 CET for customer payments. "
                "Payments that miss a cut-off are re-dated to the next business day."
            ),
        ),
    ]
    return build_chunks(Corpus(documents=docs), size=40, overlap=10)
