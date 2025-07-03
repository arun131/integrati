# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for some Python packages (e.g., sqlite3)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker cache
COPY ./backend/requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of the application code
COPY ./backend/app /app/app

# Set environment variables for FastAPI (optional but good practice)
ENV PYTHONPATH=/app

# Expose the port FastAPI will run on (e.g., 8000)
EXPOSE 8000

# Command to run the application using Uvicorn (FastAPI's recommended ASGI server)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 