import pytest

from ragproof.corpus import Document, chunk_document

TEXT = " ".join(f"word{i}" for i in range(300))


def test_fixed_chunks_respect_size_and_overlap():
    doc = Document(doc_id="d", title="T", text=TEXT)
    chunks = chunk_document(doc, size=100, overlap=20, strategy="fixed")
    assert len(chunks) > 1
    assert all(len(c.text.split()) <= 100 for c in chunks)
    first, second = chunks[0].text.split(), chunks[1].text.split()
    assert first[-20:] == second[:20], "consecutive windows must share the overlap"


def test_fixed_chunks_cover_the_whole_document():
    doc = Document(doc_id="d", title="T", text=TEXT)
    chunks = chunk_document(doc, size=100, overlap=20, strategy="fixed")
    covered = set()
    for chunk in chunks:
        covered.update(chunk.text.split())
    assert covered == set(TEXT.split())


def test_sentence_chunks_do_not_split_sentences():
    text = " ".join(f"This is sentence number {i} in the document." for i in range(40))
    doc = Document(doc_id="d", title="T", text=text)
    chunks = chunk_document(doc, size=50, overlap=12, strategy="sentence")
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.text.strip().endswith("."), "sentence chunks end on a boundary"


def test_chunk_ids_are_stable_and_unique():
    doc = Document(doc_id="alpha", title="T", text=TEXT)
    a = chunk_document(doc, size=80, overlap=10)
    b = chunk_document(doc, size=80, overlap=10)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
    assert len({c.chunk_id for c in a}) == len(a)
    assert a[0].chunk_id == "alpha::0"


def test_empty_document_yields_no_chunks():
    assert chunk_document(Document(doc_id="d", title="T", text="  ")) == []


@pytest.mark.parametrize("size,overlap", [(0, 0), (10, 10), (10, 20), (10, -1)])
def test_invalid_chunk_parameters_are_rejected(size, overlap):
    doc = Document(doc_id="d", title="T", text=TEXT)
    with pytest.raises(ValueError):
        chunk_document(doc, size=size, overlap=overlap)


def test_unknown_strategy_is_rejected():
    with pytest.raises(ValueError, match="unknown chunking strategy"):
        chunk_document(Document(doc_id="d", title="T", text=TEXT), strategy="magic")
