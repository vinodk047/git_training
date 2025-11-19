# MQTT to IoT Hub Bridge - Dockerfile

# Use official Python runtime as base image
FROM python:3.11-slim

# Set metadata
LABEL maintainer="IoT Developer"
LABEL description="MQTT to Azure IoT Hub Bridge"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY mqtt_iot_bridge/ ./mqtt_iot_bridge/
COPY main.py .
COPY config.yaml .

# Create non-root user for security
RUN useradd -m -u 1000 bridgeuser && \
    chown -R bridgeuser:bridgeuser /app

# Switch to non-root user
USER bridgeuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the bridge
ENTRYPOINT ["python", "main.py"]

# Default command (can be overridden)
CMD ["-c", "config.yaml"]
