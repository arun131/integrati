#!/bin/bash
set -e

# Start FastAPI backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# (Removed fastmcp server startup)

wait 