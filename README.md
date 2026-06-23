# Arize Evaluation — LLM Trace Generator

An LLM app whose job is to generate traces into **Arize AX** so the
platform can be evaluated (tracing quality, out-of-the-box evaluators, etc.).
Starts as a local cron job; can be containerized and deployed to Minikube
later without changing the Arize wiring.

## 1. Setup

```bash
# from the repo root
python3 -m venv .venv
source .venv/bin/activate        # confirm: `which python` points inside .venv
pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Environment variables

### Option A — a local `.env` file (easiest for local dev)

```bash
cp .env.example .env
# edit .env and fill in your real values
```

Then load it into your shell before running:

```bash
set -a; source .env; set +a
python run_once.py
```

`.env` is gitignored.

### Option B — export directly in your shell

```bash
export ARIZE_SPACE_ID="..."     # from the Arize AX UI
export ARIZE_API_KEY="..."      # from the Arize AX UI
export ARIZE_PROJECT="arize-eval-demo"
export OPENAI_API_KEY="..."
python run_once.py
```

Either way, `app.py` reads them via `os.environ`. Where to get the Arize values:
in the **Arize AX UI**, find your **Space ID** and create an **API key**.

## 3. First run

```bash
set -a; source .env; set +a
python run_once.py
```

Then open your Arize AX project and confirm the traces appeared. That single
successful run proves the whole pipeline: credentials -> instrumentation ->
export -> traces in AX.

## 4. Run continuously via cron

Edit your crontab:

```bash
crontab -e
```

Add a line to run every 5 minutes (adjust the path to your repo):

```cron
*/5 * * * * cd /home/imen/Desktop/arize_eval_app && /home/imen/Desktop/arize_eval_app/.venv/bin/python run_once.py >> /home/imen/Desktop/arize_eval_app/cron.log 2>&1
```

Notes:
- Cron does not load your `.env` automatically, so either keep the env vars in
  the crontab itself, or add `set -a; . /path/.env; set +a;` into a small
  wrapper script that cron calls.
- Use the venv's python (`.venv/bin/python`) explicitly — cron has a minimal
  PATH and will not know about your activated venv.
- Logs go to `cron.log` so you can check it ran.
## 5. Later: deploy to Minikube (optional)

When/if you need always-on or infrastructure-realistic traces, containerize
this same app and deploy it. The Arize wiring in `app.py` does **not** change —
only where the credentials come from: in Kubernetes you provide them as a
**Secret** mounted as environment variables, instead of a `.env` file.

## Files

- `app.py` — the LLM app + Arize tracing setup
- `run_once.py` — one batch run, called by cron
- `.env.example` — documents the required env vars (copy to `.env`)
- `requirements.txt` — dependencies
- `.gitignore` — keeps `.env` and `.venv` out of git
