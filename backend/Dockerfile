# backend/Dockerfile
FROM python:3.12-slim

# System deps for faiss + building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Install torch CPU first — this layer changes rarely, so it caches
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.4.1 \
    --index-url https://download.pytorch.org/whl/cpu

# 2. Install the rest — only re-runs when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Pre-download the embedding model — bakes it into the image
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# 4. Copy app code LAST — code changes only invalidate this layer
COPY app ./app
RUN mkdir -p /app/data

# Render uses port 10000 by default, but we keep 8000 as a fallback for local testing
EXPOSE 8000

# The change is here: use ${PORT} if it exists, otherwise default to 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]