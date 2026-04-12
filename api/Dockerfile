FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY api/requirements.txt /app/api/requirements.txt
COPY pipeline/requirements.txt /app/pipeline/requirements.txt

# The API image includes the local trigger path, which reuses the pipeline entry
# point inside the same repo checkout. Install both requirement sets so the
# local dispatch path and cloud dispatch path share one truthful container.
RUN pip install --no-cache-dir -r /app/api/requirements.txt -r /app/pipeline/requirements.txt

COPY api /app/api
COPY pipeline /app/pipeline
COPY shared /app/shared

WORKDIR /app/api

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "wsgi:app"]
