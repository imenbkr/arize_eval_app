.PHONY: docs phoenix ask eval readme test dashboard

export PYTHONPATH := src
PY := .venv/bin/python

docs:
	rm -rf data/otel data/docs
	git clone -q --depth 1 --filter=blob:none --sparse https://github.com/open-telemetry/opentelemetry.io data/otel
	git -C data/otel sparse-checkout set content/en/docs/concepts
	cp -r data/otel/content/en/docs/concepts data/docs

phoenix:
	docker compose up -d phoenix

ask:
	$(PY) src/ask.py "$(Q)"

eval:
	$(PY) evals/run_evals.py

readme:
	$(PY) evals/update_readme.py

test:
	$(PY) -m pytest -q tests

dashboard:
	$(PY) dashboards/arize_dashboard.py --project $(or $(PROJECT),rag-eval-experiments)
