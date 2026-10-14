"""LLM-as-judge: a larger model grades the answers of the smaller ones."""
import json
import os
import re

from rag import client

JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "meta-llama/llama-3.3-70b-instruct")
PROMPTS = {
    "hallucination": (
        "Context:\n{context}\n\nAnswer:\n{answer}\n\n"
        "Is every claim in the answer supported by the context? "
        "An answer of \"I don't know\" counts as factual. "
        'Reply only with JSON: {{"label": "factual" or "hallucinated", "explanation": "..."}}'
    ),
    "correctness": (
        "Question:\n{question}\n\nReference answer:\n{reference}\n\nAnswer:\n{answer}\n\n"
        "Does the answer match the reference in meaning? "
        'Reply only with JSON: {{"label": "correct" or "incorrect", "explanation": "..."}}'
    ),
}


def judge(kind, **fields):
    resp = client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
        max_tokens=200,
        messages=[{"role": "user", "content": PROMPTS[kind].format(**fields)}],
    )
    return json.loads(re.search(r"\{.*\}", resp.choices[0].message.content, re.S).group())
