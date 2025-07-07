# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for some Python packages (e.g., sqlite3)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsqlite3-dev \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (universal virtualenv/package manager)
RUN pip install uv

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt using uv
RUN uv pip install --system --no-cache-dir -r /app/requirements.txt

# Copy the rest of the application code
COPY app /app/app

# Set environment variables for FastAPI (optional but good practice)
ENV PYTHONPATH=/app

# Expose the port FastAPI will run on (e.g., 8000)
EXPOSE 8000
EXPOSE 9000

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"] 