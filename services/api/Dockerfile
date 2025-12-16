FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY services/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Ship the services code inside the image so imports work
# even if the repo volume/PYTHONPATH is misconfigured at runtime.
COPY services /app/services

# Ship the website + challenge assets in the image as a fallback,
# so the service still works even if the repo volume mount is wrong.
COPY index.html /app/index.html
COPY static /app/static
COPY challenges /app/challenges

# We mount the repo at runtime for challenges/artifacts.
# Use a tiny launcher that bootstraps sys.path reliably.
CMD ["python", "/app/services/api/app/run.py"]

