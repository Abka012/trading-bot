# Optimized Dockerfile for Render
# Multi-stage build for smaller image size and better caching

# =============================================================================
# Stage 1: Build dependencies
# =============================================================================
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libhdf5-dev \
    libatlas-base-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Runtime image
# =============================================================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libatlas-base-dev \
    libhdf5-serial-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Create directory for model artifacts if it doesn't exist
RUN mkdir -p /app/tradingBot/artifacts/models \
    && mkdir -p /app/tradingBot/outputs/trades \
    && mkdir -p /app/tradingBot/outputs/equity \
    && mkdir -p /app/tradingBot/outputs/logs \
    && mkdir -p /app/tradingBot/outputs/reports

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
# Note: Running as root for now due to TensorFlow permissions
# Uncomment below if you resolve TensorFlow permission issues
# USER appuser

# Expose port (Render uses PORT env variable, default to 8000)
EXPOSE 8000

# Health check for Render monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f\"http://localhost:{os.getenv('PORT','8000')}/api/health\")" || exit 1

# Run with production settings
# Render sets PORT env variable automatically
CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 2"]
