"""Run the golden set through each model, judge every answer, and gate on hallucinations.

Each case is wrapped in an EVALUATOR span whose `metadata` carries the run id,
model and judge labels, so Phoenix / Arize can filter and chart them.
Outputs results/results.csv and results/summary.md; exits 1 if the gate fails.
"""
import csv
import json
import os
import sys
import time
from pathlib import Path

from openai import APIStatusError

from opentelemetry import trace

from tracing import setup_tracing
from rag import Retriever, load_chunks, answer
from judge import judge, JUDGE_MODEL

MODELS = os.environ.get(
    "EVAL_MODELS",
    "meta-llama/llama-3.1-8b-instruct,qwen/qwen-2.5-7b-instruct,mistralai/mistral-7b-instruct",
).split(",")
GATE_MODEL = os.environ.get("GATE_MODEL", MODELS[0])
MAX_HALLUCINATION = float(os.environ.get("MAX_HALLUCINATION", "0.10"))
LIMIT = int(os.environ.get("EVAL_LIMIT", "0"))  # 0 = whole golden set
RUN_ID = os.environ.get("RUN_ID", time.strftime("%Y%m%d-%H%M"))

tp = setup_tracing("rag-eval-experiments")
tracer = trace.get_tracer("evals")
retriever = Retriever(load_chunks())
golden = [json.loads(l) for l in Path("evals/golden.jsonl").read_text().splitlines() if l.strip()]
if LIMIT:
    golden = golden[:LIMIT]

rows = []
stopped = None


def run_case(model, g):
    with tracer.start_as_current_span("eval_case") as span:
        span.set_attribute("openinference.span.kind", "EVALUATOR")
        span.set_attribute("input.value", g["question"])
        out, ctx = answer(g["question"], retriever, model)
        h = judge("hallucination", context=ctx, answer=out)
        c = judge("correctness", question=g["question"], reference=g["reference"], answer=out)
        span.set_attribute("output.value", out)
        span.set_attribute("metadata", json.dumps({
            "run_id": RUN_ID, "model": model,
            "hallucination": h["label"], "correctness": c["label"],
        }))
    return {"run_id": RUN_ID, "model": model, **g, "answer": out,
            "hallucination": h["label"], "correctness": c["label"],
            "h_explanation": h["explanation"], "c_explanation": c["explanation"]}


for model in MODELS:
    for i, g in enumerate(golden, 1):
        try:
            row = run_case(model, g)
        except APIStatusError as e:
            # e.g. 402 out of credits: keep what we have and stop cleanly
            stopped = f"provider error {e.status_code} at {model} case {i}"
            print("STOPPED:", stopped, flush=True)
            break
        rows.append(row)
        print(f"[{model}] {i}/{len(golden)} {row['hallucination']}/{row['correctness']}", flush=True)
    if stopped:
        break

if not rows:
    sys.exit(f"No results: {stopped}")
Path("results").mkdir(exist_ok=True)
with open("results/results.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)

lines = ["| Model | Hallucination rate | Correctness |", "|---|---|---|"]
rates = {}
for m in MODELS:
    r = [x for x in rows if x["model"] == m]
    if not r:
        continue
    rates[m] = sum(x["hallucination"] == "hallucinated" for x in r) / len(r)
    correct = sum(x["correctness"] == "correct" for x in r) / len(r)
    lines.append(f"| `{m}` | {rates[m]:.0%} | {correct:.0%} |")
note = f"_Run `{RUN_ID}` · {len(golden)} golden questions per model · judge: `{JUDGE_MODEL}`_"
if stopped:
    note += f"\n\n**Partial run:** {stopped}."
Path("results/summary.md").write_text("\n".join(lines) + "\n\n" + note + "\n")
print("\n".join(lines))

if tp:
    tp.force_flush()
if stopped or GATE_MODEL not in rates:
    sys.exit(f"INCOMPLETE: {stopped}")
if rates[GATE_MODEL] > MAX_HALLUCINATION:
    sys.exit(f"GATE FAILED: {GATE_MODEL} hallucination {rates[GATE_MODEL]:.0%} > {MAX_HALLUCINATION:.0%}")
print("GATE PASSED")
