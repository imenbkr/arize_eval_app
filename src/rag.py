"""RAG assistant over the OpenTelemetry concept docs.

Retrieval is TF-IDF (no embedding API needed). Each question produces a
CHAIN span with a RETRIEVER child span; the OpenAI instrumentor adds the
LLM span. Models are served by OpenRouter (OpenAI-compatible API).
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from opentelemetry import trace
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)
tracer = trace.get_tracer(__name__)

DEFAULT_MODEL = os.environ.get("LLM_MODEL", "meta-llama/llama-3.1-8b-instruct")
SYSTEM = (
    "Answer only from the context. "
    "If the context does not contain the answer, reply exactly: I don't know."
)


def load_chunks(docs_dir="data/docs", size=800):
    chunks = []
    for f in sorted(Path(docs_dir).rglob("*.md")):
        text = f.read_text(errors="ignore")
        chunks += [
            {"source": str(f.relative_to(docs_dir)), "text": text[i:i + size]}
            for i in range(0, len(text), size)
        ]
    return chunks


class Retriever:
    def __init__(self, chunks):
        self.chunks = chunks
        self.vec = TfidfVectorizer(stop_words="english")
        self.matrix = self.vec.fit_transform([c["text"] for c in chunks])

    def search(self, question, k=4):
        with tracer.start_as_current_span("retrieve") as span:
            span.set_attribute("openinference.span.kind", "RETRIEVER")
            span.set_attribute("input.value", question)
            scores = cosine_similarity(self.vec.transform([question]), self.matrix)[0]
            top = scores.argsort()[::-1][:k]
            for j, i in enumerate(top):
                span.set_attribute(f"retrieval.documents.{j}.document.id", self.chunks[i]["source"])
                span.set_attribute(f"retrieval.documents.{j}.document.content", self.chunks[i]["text"])
                span.set_attribute(f"retrieval.documents.{j}.document.score", float(scores[i]))
            return [self.chunks[i] for i in top]


def answer(question, retriever, model=DEFAULT_MODEL):
    """One question = one CHAIN span (retrieve + LLM call)."""
    with tracer.start_as_current_span("rag") as span:
        span.set_attribute("openinference.span.kind", "CHAIN")
        span.set_attribute("input.value", question)
        context = "\n\n".join(d["text"] for d in retriever.search(question))
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=300,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
            ],
        )
        out = resp.choices[0].message.content
        span.set_attribute("output.value", out)
        return out, context
