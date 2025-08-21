#!/usr/bin/env python3
"""
Local development server for integrati backend.
Run this script to start the backend locally for faster debugging.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set environment variables for local development
os.environ.setdefault("DEBUG_MODE", "true")
os.environ.setdefault("STORAGE_BACKEND", "sqlite")
os.environ.setdefault("LOG_LEVEL", "DEBUG")

if __name__ == "__main__":
    print("Starting integrati backend in local development mode...")
    print("Make sure you have Redis running or set STORAGE_BACKEND=sqlite")

    try:
        import uvicorn

        # Import app for type checking but not used directly
        from mcp_plexus.main import app  # noqa: F401

        uvicorn.run(
            "mcp_plexus.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="debug",
        )
    except ImportError as e:
        print(f"Import error: {e}")
        print(
            "Make sure you're in the integrati_backend directory and have dependencies installed"
        )
        print("Run: cd integrati_backend && uv sync")
