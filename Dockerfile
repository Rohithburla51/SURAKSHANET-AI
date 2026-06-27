# SurakshaNet AI — FastAPI Backend Docker Image
# Optimized for Hugging Face Spaces (port 7860, no cold starts)

FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    libsm6 \
    libxext6 \
    libxrender-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ /app/

# Create necessary directories
RUN mkdir -p /app/logs

# Expose port (Hugging Face Spaces uses 7860)
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:7860/health')"

# Run FastAPI with Uvicorn
# Hugging Face Spaces sets PORT env var; default to 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
