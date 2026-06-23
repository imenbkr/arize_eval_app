# Minimal image for the Arize trace-generator app.
FROM python:3.12-slim

WORKDIR /app

# Install deps first (better layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the app code.
COPY app.py run_once.py ./

# Default command runs one batch and exits. In Kubernetes this is run on a
# schedule via a CronJob (see k8s/cronjob.yaml), which is the deployed
# equivalent of the local cron job.
CMD ["python", "run_once.py"]
