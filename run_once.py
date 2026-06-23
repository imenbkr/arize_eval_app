"""
Single batch run — this is what cron calls.

Each invocation sets up tracing once, then sends every prompt through the
LLM (one trace each) to Arize AX, and exits. Running it on a schedule
(e.g. every 5 minutes via cron) produces a continuous stream of traces
without needing a deployed, always-on service.

Usage:
    python run_once.py
"""
import time
from app import setup_tracing, answer, PROMPTS


def main():
    setup_tracing()
    print(f"Sending {len(PROMPTS)} prompts to Arize...")
    for i, q in enumerate(PROMPTS, start=1):
        try:
            out = answer(q)
            print(f"[{i}/{len(PROMPTS)}] OK: {q[:50]}...")
        except Exception as e:
            print(f"[{i}/{len(PROMPTS)}] ERROR on '{q[:50]}...': {e}")
        time.sleep(1)  # small gap so traces have distinct timestamps

    # Traces are exported asynchronously; give the exporter a moment to flush
    # before the process exits, otherwise the last spans may be dropped.
    print("Flushing traces...")
    time.sleep(5)
    print("Done. Check your Arize AX project for the traces.")


if __name__ == "__main__":
    main()
