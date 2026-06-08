# Hugging Face Spaces — FastAPI backend
# Base image: Python 3.11 slim (matches our pinned version, keeps image lean)
FROM python:3.11-slim

# HF Spaces requires the app to listen on port 7860
ENV PORT=7860

# Keeps Python from buffering stdout/stderr (better logging)
ENV PYTHONUNBUFFERED=1

# Cache sentence-transformers model inside the image at build time
# so the first request isn't slow waiting for a download
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers

WORKDIR /app

# Install system deps needed by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (Docker layer cache —
# only re-runs if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model into the image at build time
# This means zero cold-start delay for embeddings on first request
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy the rest of the app
COPY app/ ./app/

# HF Spaces expects the app on 0.0.0.0:7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
