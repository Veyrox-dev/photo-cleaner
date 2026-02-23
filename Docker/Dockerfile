# PhotoCleaner Docker Image
# Build: docker build -t photocleaner:0.5.5 .
# Run:   docker run -v /path/to/photos:/data photocleaner:0.5.5

FROM python:3.12-slim

LABEL maintainer="PhotoCleaner Team"
LABEL version="0.5.5"
LABEL description="Intelligent photo management with AI-powered duplicate detection"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY run_ui.py .
COPY pyproject.toml .
COPY README.md .
COPY LICENSE .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PHOTOCLEANER_MODE=RELEASE

# Create volume mount point
VOLUME ["/data"]

# Default command (can be overridden)
CMD ["python", "run_ui.py"]
