# Image for the RAG app and its eval suite.
FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git make \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY Makefile ./
COPY src/ src/
COPY evals/ evals/
RUN make docs PY=python

ENV PYTHONPATH=src
# Default: one eval run, traced to the backend set by TRACING_BACKEND.
CMD ["python", "evals/run_evals.py"]
