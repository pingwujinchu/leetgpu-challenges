FROM micr.cloud.mioffice.cn/cloudml-preset/cuda:12.9.1-py3.12-ubuntu22.04-0.1

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY services/worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services /app/services

CMD ["python", "/app/services/worker/app/worker.py"]

