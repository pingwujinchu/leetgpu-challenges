FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Needed when JOB_EXECUTOR=docker (we run `docker run ...` from inside this container).
# This assumes the host docker daemon is reachable via /var/run/docker.sock (mounted in compose).
RUN apt-get update && apt-get install -y --no-install-recommends docker.io ca-certificates && rm -rf /var/lib/apt/lists/*

COPY services/worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services /app/services

CMD ["python", "/app/services/worker/app/worker.py"]

