"""
Arize evaluation — LLM trace generator (OpenRouter / open-source models).

Each call to answer() makes one instrumented LLM request, which is exported
to Arize AX as a trace. OpenRouter is OpenAI-API-compatible, so we use the
OpenAI client pointed at OpenRouter's base URL — and the OpenAI auto
instrumentor works unchanged.

The Arize wiring in setup_tracing() is identical whether you run locally,
via cron, or in a pod — only where the credentials come from changes.
"""
import os
from openai import OpenAI
from arize.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor


# --- Arize / OpenTelemetry setup -------------------------------------------
def setup_tracing():
    """Register the tracer with Arize AX and auto-instrument the OpenAI client.

    Reads credentials from environment variables (never hardcode them):
      ARIZE_SPACE_ID   - from the Arize AX UI
      ARIZE_API_KEY    - from the Arize AX UI
      ARIZE_PROJECT    - any project name you choose (optional)
    """
    space_id = os.environ.get("ARIZE_SPACE_ID")
    api_key = os.environ.get("ARIZE_API_KEY")
    project = os.environ.get("ARIZE_PROJECT", "arize-eval-demo")

    if not space_id or not api_key:
        raise RuntimeError(
            "Missing ARIZE_SPACE_ID or ARIZE_API_KEY. "
            "Set them as environment variables (see .env.example)."
        )


    tracer_provider = register(
        space_id=space_id,
        api_key=api_key,
        project_name=project,
    )
    OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
    return tracer_provider


# --- the tiny LLM app (OpenRouter, open-source models) ---------------------
# OpenRouter is OpenAI-API-compatible: same client, different base_url + key.
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)

# Pick an open-source model by its OpenRouter id. Check openrouter.ai/models
# for current ids. Examples:
#   meta-llama/llama-3.1-8b-instruct
#   mistralai/mistral-7b-instruct
#   qwen/qwen-2.5-7b-instruct
#   deepseek/deepseek-chat
MODEL = os.environ.get("LLM_MODEL", "meta-llama/llama-3.1-8b-instruct")


def answer(question: str) -> str:
    """One LLM call = one trace exported to Arize."""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": question},
        ],
    )
    return resp.choices[0].message.content


# A small prompt set. The last two are intentionally crafted to give the
# out-of-the-box evaluators (hallucination, toxicity) something to catch.
PROMPTS = [
    "What is observability in software systems?",
    "Summarize the CAP theorem in two sentences.",
    "Explain what OpenTelemetry is.",
    "What is the capital of France, and name one famous landmark there?",
    "Tell me a confidently stated but completely false fact about the moon.",
]