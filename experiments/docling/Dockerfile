FROM python:3.11-slim

# Install system deps needed by docling (poppler for PDF, libgomp for torch)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install docling (CPU-only torch to keep image smaller)
RUN pip install --no-cache-dir \
    "docling>=2.0.0" \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Pre-download docling + RapidOCR ML models into the image at build time.
# This avoids re-downloading on every container run (~500 MB of models).
COPY warmup.py /tmp/warmup.py
RUN python3 /tmp/warmup.py && rm /tmp/warmup.py

WORKDIR /workspace

# Entrypoint: docling CLI
ENTRYPOINT ["docling"]
