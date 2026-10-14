"""Tracing setup: Phoenix (local, default), Arize AX, or none (CI).

The backend is picked with TRACING_BACKEND=phoenix|arize|none. The OpenAI
client is auto-instrumented, so every LLM call becomes an LLM span.
"""
import os
from openinference.instrumentation.openai import OpenAIInstrumentor


def setup_tracing(project="rag-eval"):
    backend = os.environ.get("TRACING_BACKEND", "phoenix")
    if backend == "none":
        return None
    if backend == "arize":
        from arize.otel import register
        tp = register(
            space_id=os.environ["ARIZE_SPACE_ID"],
            api_key=os.environ["ARIZE_API_KEY"],
            project_name=project,
        )
    else:
        from phoenix.otel import register
        tp = register(
            project_name=project,
            endpoint=os.environ.get("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces"),
        )
    OpenAIInstrumentor().instrument(tracer_provider=tp)
    return tp
