"""Analytics database for storing and querying analytics data."""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List
import os

from .models import (
    MCPRequestLog,
    AuthEventLog,
    IntegrationEventLog,
    AnalyticsSummary,
    UserAnalytics,
    UserNotification,
)

logger = logging.getLogger(__name__)


# Import the same data directory function from settings
def get_data_directory() -> Path:
    """Determine the appropriate data directory based on environment."""
    # Check if we're running in Docker (common Docker environment variables)
    is_docker = any(
        [
            os.path.exists("/.dockerenv"),  # Docker creates this file
            os.environ.get("DOCKER_CONTAINER") == "true",
            os.environ.get("KUBERNETES_SERVICE_HOST"),  # Kubernetes
        ]
    )

    if is_docker:
        # In Docker, use /app/data (mounted volume)
        data_dir = Path("/app/data")
    else:
        # Local development, use project-relative path
        # Go up two levels from this file to get to integrati_backend root
        project_root = Path(__file__).parent.parent.resolve()
        data_dir = project_root / "data"

    # Ensure the data directory exists
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class AnalyticsDatabase:
    """SQLite database for storing analytics data."""

    def __init__(self, db_path: str = None):
        """Initialize analytics database."""
        if db_path is None:
            # Use dynamic path based on environment
            db_path = str(get_data_directory() / "analytics.db")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # MCP Request Logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mcp_request_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    config_id TEXT NOT NULL,
                    client_name TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    response TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    session_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Auth Event Logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auth_event_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Integration Event Logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS integration_event_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    integration_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # User Notifications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    notification_id TEXT NOT NULL UNIQUE,
                    notification_text TEXT NOT NULL,
                    integration_type TEXT NOT NULL,
                    agent_used TEXT NOT NULL,
                    priority TEXT DEFAULT 'normal',
                    timestamp TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT 0,
                    event_details TEXT,
                    tools_used TEXT,
                    reasoning TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for better query performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_mcp_entity_user ON mcp_request_logs(entity_id, user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_mcp_timestamp ON mcp_request_logs(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_mcp_tool_name ON mcp_request_logs(tool_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_mcp_client_name ON mcp_request_logs(client_name)"
            )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_auth_entity_user ON auth_event_logs(entity_id, user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_auth_timestamp ON auth_event_logs(timestamp)"
            )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_integration_entity_user ON integration_event_logs(entity_id, user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_integration_timestamp ON integration_event_logs(timestamp)"
            )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_notifications_entity_user ON user_notifications(entity_id, user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_notifications_timestamp ON user_notifications(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON user_notifications(is_read)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_notifications_notification_id ON user_notifications(notification_id)"
            )

            conn.commit()

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection with proper async context management."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    async def insert_mcp_request_log(self, log: MCPRequestLog) -> bool:
        """Insert MCP request log into database."""
        try:
            async with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO mcp_request_logs
                    (entity_id, user_id, config_id, client_name, tool_name, parameters, response,
                     execution_time, timestamp, success, error_message, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        log.entity_id,
                        log.user_id,
                        log.config_id,
                        log.client_name,
                        log.tool_name,
                        json.dumps(log.parameters),
                        json.dumps(log.response),
                        log.execution_time,
                        log.timestamp.isoformat(),
                        log.success,
                        log.error_message,
                        log.session_id,
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error inserting MCP request log: {e}")
            return False

    async def insert_auth_event_log(self, log: AuthEventLog) -> bool:
        """Insert auth event log into database."""
        try:
            async with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO auth_event_logs
                    (entity_id, user_id, event_type, timestamp, metadata, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        log.entity_id,
                        log.user_id,
                        log.event_type,
                        log.timestamp.isoformat(),
                        json.dumps(log.metadata) if log.metadata else None,
                        log.success,
                        log.error_message,
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error inserting auth event log: {e}")
            return False

    async def insert_integration_event_log(self, log: IntegrationEventLog) -> bool:
        """Insert integration event log into database."""
        try:
            async with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO integration_event_logs
                    (entity_id, user_id, integration_name, event_type, timestamp, metadata, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        log.entity_id,
                        log.user_id,
                        log.integration_name,
                        log.event_type,
                        log.timestamp.isoformat(),
                        json.dumps(log.metadata) if log.metadata else None,
                        log.success,
                        log.error_message,
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error inserting integration event log: {e}")
            return False

    async def get_analytics_summary(
        self, entity_id: str, days: int = 30
    ) -> AnalyticsSummary:
        """Get analytics summary for a tenant."""
        try:
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

            async with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get total requests
                cursor.execute(
                    """
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
                           SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed,
                           AVG(execution_time) as avg_time
                    FROM mcp_request_logs
                    WHERE entity_id = ? AND timestamp >= ?
                """,
                    (entity_id, start_date),
                )

                result = cursor.fetchone()
                total_requests = result["total"] or 0
                successful_requests = result["successful"] or 0
                failed_requests = result["failed"] or 0
                avg_execution_time = result["avg_time"] or 0.0

                # Get most used tools
                cursor.execute(
                    """
                    SELECT tool_name, COUNT(*) as count
                    FROM mcp_request_logs
                    WHERE entity_id = ? AND timestamp >= ?
                    GROUP BY tool_name
                    ORDER BY count DESC
                    LIMIT 10
                """,
                    (entity_id, start_date),
                )

                most_used_tools = [
                    {"tool_name": row["tool_name"], "count": row["count"]}
                    for row in cursor.fetchall()
                ]

                # Get client usage
                cursor.execute(
                    """
                    SELECT client_name, COUNT(*) as count
                    FROM mcp_request_logs
                    WHERE entity_id = ? AND timestamp >= ?
                    GROUP BY client_name
                """,
                    (entity_id, start_date),
                )

                client_usage = {
                    row["client_name"]: row["count"] for row in cursor.fetchall()
                }

                return AnalyticsSummary(
                    total_requests=total_requests,
                    successful_requests=successful_requests,
                    failed_requests=failed_requests,
                    average_execution_time=avg_execution_time,
                    most_used_tools=most_used_tools,
                    client_usage=client_usage,
                    time_period={
                        "start": start_date,
                        "end": datetime.utcnow().isoformat(),
                    },
                )
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return AnalyticsSummary(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                average_execution_time=0.0,
                most_used_tools=[],
                client_usage={},
                time_period={"start": start_date, "end": datetime.utcnow().isoformat()},
            )

    async def get_user_analytics(
        self, entity_id: str, user_id: str, days: int = 30
    ) -> UserAnalytics:
        """Get analytics for a specific user."""
        try:
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

            async with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get user request statistics
                cursor.execute(
                    """
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
                           SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed,
                           AVG(execution_time) as avg_time
                    FROM mcp_request_logs
                    WHERE entity_id = ? AND user_id = ? AND timestamp >= ?
                """,
                    (entity_id, user_id, start_date),
                )

                result = cursor.fetchone()
                total_requests = result["total"] or 0
                successful_requests = result["successful"] or 0
                failed_requests = result["failed"] or 0
                avg_execution_time = result["avg_time"] or 0.0

                # Get favorite tools
                cursor.execute(
                    """
                    SELECT tool_name, COUNT(*) as count
                    FROM mcp_request_logs
                    WHERE entity_id = ? AND user_id = ? AND timestamp >= ?
                    GROUP BY tool_name
                    ORDER BY count DESC
                    LIMIT 5
                """,
                    (entity_id, user_id, start_date),
                )

                favorite_tools = [row["tool_name"] for row in cursor.fetchall()]

                # Get last activity
                cursor.execute(
                    """
                    SELECT MAX(timestamp) as last_activity
                    FROM mcp_request_logs
                    WHERE entity_id = ? AND user_id = ?
                """,
                    (entity_id, user_id),
                )

                result = cursor.fetchone()
                last_activity = None
                if result and result["last_activity"]:
                    last_activity = datetime.fromisoformat(result["last_activity"])

                # Get integrations used
                cursor.execute(
                    """
                    SELECT DISTINCT integration_name
                    FROM integration_event_logs
                    WHERE entity_id = ? AND user_id = ? AND success = 1
                """,
                    (entity_id, user_id),
                )

                integrations_used = [
                    row["integration_name"] for row in cursor.fetchall()
                ]

                return UserAnalytics(
                    user_id=user_id,
                    entity_id=entity_id,
                    total_requests=total_requests,
                    successful_requests=successful_requests,
                    failed_requests=failed_requests,
                    average_execution_time=avg_execution_time,
                    favorite_tools=favorite_tools,
                    last_activity=last_activity,
                    integrations_used=integrations_used,
                )
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return UserAnalytics(
                user_id=user_id,
                entity_id=entity_id,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                average_execution_time=0.0,
                favorite_tools=[],
                last_activity=None,
                integrations_used=[],
            )

    async def insert_user_notification(self, notification: UserNotification) -> bool:
        """Insert user notification into database."""
        try:
            async with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO user_notifications
                    (entity_id, user_id, notification_id, notification_text, integration_type,
                     agent_used, priority, timestamp, is_read, event_details, tools_used, reasoning)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        notification.entity_id,
                        notification.user_id,
                        notification.notification_id,
                        notification.notification_text,
                        notification.integration_type,
                        notification.agent_used,
                        notification.priority,
                        notification.timestamp.isoformat(),
                        notification.is_read,
                        json.dumps(notification.event_details)
                        if notification.event_details
                        else None,
                        json.dumps(notification.tools_used)
                        if notification.tools_used
                        else None,
                        notification.reasoning,
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error inserting user notification: {e}")
            return False

    async def get_user_notifications(
        self, entity_id: str, user_id: str, limit: int = 20, include_read: bool = False
    ) -> List[UserNotification]:
        """Get notifications for a user."""
        try:
            async with self.get_connection() as conn:
                cursor = conn.cursor()

                # Build query based on whether to include read notifications
                query = """
                    SELECT * FROM user_notifications
                    WHERE entity_id = ? AND user_id = ?
                """
                params = [entity_id, user_id]

                if not include_read:
                    query += " AND is_read = 0"

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                notifications = []
                for row in rows:
                    notification = UserNotification(
                        entity_id=row["entity_id"],
                        user_id=row["user_id"],
                        notification_id=row["notification_id"],
                        notification_text=row["notification_text"],
                        integration_type=row["integration_type"],
                        agent_used=row["agent_used"],
                        priority=row["priority"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        is_read=bool(row["is_read"]),
                        event_details=json.loads(row["event_details"])
                        if row["event_details"]
                        else None,
                        tools_used=json.loads(row["tools_used"])
                        if row["tools_used"]
                        else None,
                        reasoning=row["reasoning"],
                    )
                    notifications.append(notification)

                return notifications
        except Exception as e:
            logger.error(f"Error getting user notifications: {e}")
            return []

    async def mark_notification_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        try:
            async with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE user_notifications SET is_read = 1 WHERE notification_id = ?",
                    (notification_id,),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False

    async def mark_all_notifications_as_read(
        self, entity_id: str, user_id: str
    ) -> bool:
        """Mark all notifications as read for a user."""
        try:
            async with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE user_notifications
                    SET is_read = 1
                    WHERE entity_id = ? AND user_id = ? AND is_read = 0
                    """,
                    (entity_id, user_id),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            return False

    async def get_unread_notification_count(self, entity_id: str, user_id: str) -> int:
        """Get count of unread notifications for a user."""
        try:
            async with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM user_notifications
                    WHERE entity_id = ? AND user_id = ? AND is_read = 0
                    """,
                    (entity_id, user_id),
                )
                result = cursor.fetchone()
                return result["count"] if result else 0
        except Exception as e:
            logger.error(f"Error getting unread notification count: {e}")
            return 0
