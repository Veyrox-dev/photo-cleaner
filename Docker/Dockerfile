# PhotoCleaner Docker Image
# Build:      docker build -f Docker/Dockerfile -t photocleaner:0.8.4 .
# Smoke-Test: docker run --rm photocleaner:0.8.4 python -m photo_cleaner.cli --help
# CLI index:  docker run --rm -v C:/fotos:/data photocleaner:0.8.4 python -m photo_cleaner.cli index /data

FROM python:3.12-slim

LABEL maintainer="PhotoCleaner"
LABEL version="0.8.4"
LABEL description="Intelligent photo management with AI-powered quality analysis"

WORKDIR /app

# System-Dependencies für OpenCV, Pillow-HEIF, MediaPipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libheif1 \
    && rm -rf /var/lib/apt/lists/*

# Requirements zuerst (Docker-Layer-Cache)
COPY requirements.txt .

# PySide6 (GUI) und TensorFlow weglassen im headless Container:
# - PySide6 braucht Qt-Display-System (nicht vorhanden)
# - tensorflow/mediapipe/mtcnn sind gross und brauchen GPU/Display
# Nur CLI-relevante Dependencies installieren
RUN pip install --no-cache-dir \
    Pillow==12.1.0 \
    pillow-heif==0.13.0 \
    imagehash==4.3.1 \
    numpy==1.26.4 \
    scipy==1.11.4 \
    opencv-python-headless==4.11.0.86 \
    send2trash==1.8.2 \
    click==8.1.8 \
    cryptography==42.0.8 \
    requests==2.31.0 \
    jaraco.functools==4.0.1 \
    jaraco.context==5.3.0 \
    jaraco.text==3.12.1 \
    platformdirs==4.2.1

# App-Code
COPY src/ ./src/
COPY pyproject.toml .
COPY Docker/smoke_test.py .

# Package installieren (editable, damit cli entry point funktioniert)
RUN pip install --no-cache-dir -e . --no-deps

ENV PYTHONUNBUFFERED=1
ENV PHOTOCLEANER_MODE=RELEASE
ENV PHOTOCLEANER_HEADLESS=1

VOLUME ["/data"]

# Standard: CLI-Hilfe anzeigen (beweist Import + Startup OK)
CMD ["python", "-m", "photo_cleaner.cli", "--help"]

