# Dockerfile for MySQL to SmartSuite Sync

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./
COPY smartsuite_client.py ./

# Create necessary directories
RUN mkdir -p /app/logs /app/config

# Create non-root user
RUN useradd -m -u 1000 syncuser && \
    chown -R syncuser:syncuser /app

USER syncuser

# Volume for configuration and state
VOLUME ["/app/config", "/app/logs", "/app/sync_state.db"]

# Default command
CMD ["python", "main.py", "schedule", "--run-immediately"]
