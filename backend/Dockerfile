FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 MODELS_DIR=/app/models
# OpenCV needs glib at runtime
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the two ONNX face models (~37 MB) into the image, so the container starts ready
COPY scripts ./scripts
RUN python scripts/download_models.py /app/models

RUN useradd --create-home app && mkdir -p /app/data && chown app /app/data
USER app
COPY --chown=app app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
