#!/usr/bin/env python3
"""
Development server entry point for integrati_backend.
"""

import asyncio
import sys
import traceback
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# Import after environment setup
from mcp_plexus.main import app
from mcp_plexus.tool_loader import load_tools_from_integrations  # noqa: E402

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from the root integrati directory (parent of integrati_backend)
root_dir = project_root.parent
env_file = root_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"Loaded environment from: {env_file}")
else:
    print(f"Warning: .env file not found at {env_file}")


async def main():
    """Initialize and start the development server."""
    try:
        # Load tools from integrations
        await load_tools_from_integrations()

        return app

    except Exception as e:
        print(f"Error starting development server: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    app = asyncio.run(main())

    # Start the server
    uvicorn.run("run_dev:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
