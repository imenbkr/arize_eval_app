"""Ask one question: python src/ask.py "What is a span?" """
import sys

from tracing import setup_tracing
from rag import Retriever, load_chunks, answer

tp = setup_tracing()
out, _ = answer(sys.argv[1], Retriever(load_chunks()))
print(out)
if tp:
    tp.force_flush()
