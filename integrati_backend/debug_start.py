#!/usr/bin/env python3
"""
Debug startup script for the integrati backend.
This script can be used to start the application in debug mode.
"""

import uvicorn

if __name__ == "__main__":
    print("Starting integrati backend in debug mode...")
    print("Set breakpoints in VS Code and attach debugger to port 5678")

    uvicorn.run(
        "mcp_plexus.main:app", host="0.0.0.0", port=8000, reload=True, log_level="debug"
    )
