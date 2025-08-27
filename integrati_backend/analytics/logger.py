"""Analytics logger for tracking system activities."""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps

from .database import AnalyticsDatabase
from .models import MCPRequestLog, AuthEventLog, IntegrationEventLog

logger = logging.getLogger(__name__)


class AnalyticsLogger:
    """Main analytics logger for tracking system activities."""

    def __init__(self, db_path: str = None):
        """Initialize analytics logger."""
        if db_path is None:
            # Use dynamic path based on environment
            from .database import get_data_directory

            db_path = str(get_data_directory() / "analytics.db")

        self.db = AnalyticsDatabase(db_path)

    async def log_mcp_request(
        self,
        entity_id: str,
        user_id: str,
        config_id: str,
        client_name: str,
        tool_name: str,
        parameters: Dict[str, Any],
        response: Dict[str, Any],
        execution_time: float,
        success: bool = True,
        error_message: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> bool:
        """Log MCP tool request."""
        try:
            log_entry = MCPRequestLog(
                entity_id=entity_id,
                user_id=user_id,
                config_id=config_id,
                client_name=client_name,
                tool_name=tool_name,
                parameters=parameters,
                response=response,
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                success=success,
                error_message=error_message,
                session_id=session_id,
            )

            return await self.db.insert_mcp_request_log(log_entry)
        except Exception as e:
            logger.error(f"Error logging MCP request: {e}")
            return False

    async def log_auth_event(
        self,
        entity_id: str,
        user_id: str,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> bool:
        """Log authentication event."""
        try:
            log_entry = AuthEventLog(
                entity_id=entity_id,
                user_id=user_id,
                event_type=event_type,
                timestamp=datetime.utcnow(),
                metadata=metadata,
                success=success,
                error_message=error_message,
            )

            return await self.db.insert_auth_event_log(log_entry)
        except Exception as e:
            logger.error(f"Error logging auth event: {e}")
            return False

    async def log_integration_event(
        self,
        entity_id: str,
        user_id: str,
        integration_name: str,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> bool:
        """Log integration event."""
        try:
            log_entry = IntegrationEventLog(
                entity_id=entity_id,
                user_id=user_id,
                integration_name=integration_name,
                event_type=event_type,
                timestamp=datetime.utcnow(),
                metadata=metadata,
                success=success,
                error_message=error_message,
            )

            return await self.db.insert_integration_event_log(log_entry)
        except Exception as e:
            logger.error(f"Error logging integration event: {e}")
            return False

    async def get_analytics_summary(self, entity_id: str, days: int = 30):
        """Get analytics summary for a tenant."""
        return await self.db.get_analytics_summary(entity_id, days)

    async def get_user_analytics(self, entity_id: str, user_id: str, days: int = 30):
        """Get analytics for a specific user."""
        return await self.db.get_user_analytics(entity_id, user_id, days)


# Global logger instance
analytics_logger = AnalyticsLogger()


# Convenience functions for easy access
async def log_mcp_request(*args, **kwargs):
    """Log MCP tool request."""
    return await analytics_logger.log_mcp_request(*args, **kwargs)


async def log_auth_event(*args, **kwargs):
    """Log authentication event."""
    return await analytics_logger.log_auth_event(*args, **kwargs)


async def log_integration_event(*args, **kwargs):
    """Log integration event."""
    return await analytics_logger.log_integration_event(*args, **kwargs)


def track_mcp_request(client_name: str = "unknown"):
    """Decorator to track MCP tool requests."""

    def decorator(func):
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            response = {}

            try:
                # Extract entity_id and user_id from context
                from mcp_plexus.plexus_context import PlexusContext

                plexus_ctx = PlexusContext(ctx.fastmcp)
                entity_id = plexus_ctx.entity_id
                user_id = getattr(plexus_ctx, "user_id", "unknown")
                session_id = getattr(plexus_ctx, "mcp_session_id", None)

                # Execute the function
                result = await func(ctx, *args, **kwargs)
                response = result if isinstance(result, dict) else {"result": result}

                return result
            except Exception as e:
                success = False
                error_message = str(e)
                response = {"error": error_message}
                raise
            finally:
                # Log the request
                execution_time = time.time() - start_time

                # Get parameters (combine args and kwargs)
                parameters = {}
                if args:
                    parameters["args"] = args
                if kwargs:
                    parameters.update(kwargs)

                try:
                    await log_mcp_request(
                        entity_id=entity_id,
                        user_id=user_id,
                        client_name=client_name,
                        tool_name=func.__name__,
                        parameters=parameters,
                        response=response,
                        execution_time=execution_time,
                        success=success,
                        error_message=error_message,
                        session_id=session_id,
                    )
                except Exception as log_error:
                    logger.error(f"Error logging MCP request: {log_error}")

        return wrapper

    return decorator
