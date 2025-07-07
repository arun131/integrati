#!/bin/bash
set -e

# Start FastAPI backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Start MCP server
uvicorn app.mcp.server:app --host 0.0.0.0 --port 9000 &

wait 