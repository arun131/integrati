# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV UV_CACHE_DIR=/tmp/uv-cache

# Install system dependencies and Google Cloud SDK
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    apt-transport-https \
    lsb-release \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
        | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
        | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && apt-get update && apt-get install -y google-cloud-sdk \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy uv configuration files
COPY pyproject.toml uv.lock* ./

# Copy application code
COPY . .

# Create virtual environment and install dependencies with uv
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -r requirements.txt

# Create data directory
RUN mkdir -p /app/data

# Add bootstrap script
COPY bootstrap_and_run.sh /app/bootstrap_and_run.sh
RUN chmod +x /app/bootstrap_and_run.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the bootstrap which sets up tunnel, gcloud, then starts the app
CMD ["/app/bootstrap_and_run.sh"]
