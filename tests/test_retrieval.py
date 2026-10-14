from rag import Retriever, load_chunks


def test_retriever_returns_most_relevant_chunk():
    chunks = [
        {"source": "a.md", "text": "A span is a unit of work in a trace."},
        {"source": "b.md", "text": "Metrics are numeric measurements over time."},
    ]
    assert Retriever(chunks).search("what is a span", k=1)[0]["source"] == "a.md"


def test_load_chunks_splits_files(tmp_path):
    (tmp_path / "doc.md").write_text("x" * 1700)
    chunks = load_chunks(tmp_path, size=800)
    assert [len(c["text"]) for c in chunks] == [800, 800, 100]
    assert {c["source"] for c in chunks} == {"doc.md"}
