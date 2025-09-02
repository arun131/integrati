#!/usr/bin/env python3
"""Script to clean up ALL Gmail push subscriptions at once."""

import asyncio
import logging
import sys
import os

# Add the backend directory to Python path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from integrations.gmail.watcher import GmailWatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def cleanup_all_gmail():
    """Clean up all Gmail push subscriptions."""
    try:
        logger.info("Starting bulk cleanup of all Gmail subscriptions...")

        # Use the bulk cleanup method
        await GmailWatcher.cleanup_all_subscriptions()

        # Optionally, force stop all watches (more aggressive cleanup)
        logger.info("Force stopping all Gmail watches...")
        await GmailWatcher.force_stop_all_gmail_watches()

        logger.info("✅ All Gmail subscriptions cleaned up successfully")

    except Exception as e:
        logger.error(f"❌ Failed to cleanup Gmail subscriptions: {e}")
        sys.exit(1)


def main():
    print("📧 Gmail Bulk Cleanup Tool")
    print("This will clean up ALL Gmail push subscriptions for ALL users")
    print("")

    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        print("Cleanup cancelled.")
        return

    asyncio.run(cleanup_all_gmail())


if __name__ == "__main__":
    main()
