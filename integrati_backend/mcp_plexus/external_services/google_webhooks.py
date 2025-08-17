"""Webhook endpoints for Google push notifications (Gmail Pub/Sub, Calendar Channels)."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from integrations.gmail.watcher import GmailWatcher
from integrations.calendar.watcher import CalendarWatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/google", tags=["Google Webhooks"])


@router.post("/gmail")
async def gmail_pubsub_webhook(request: Request) -> JSONResponse:
    """Handle Gmail Pub/Sub push notifications.

    For now, minimal verification; in production, verify Google-signed JWT header.
    """
    body = await request.body()
    try:
        # Log the envelope briefly for debugging
        payload = json.loads(body.decode("utf-8"))
        logger.info(
            "Gmail Pub/Sub push received: messageId=%s",
            payload.get("message", {}).get("messageId"),
        )
    except Exception:
        pass

    watcher = GmailWatcher()
    await watcher.handle_push(headers=dict(request.headers), body=body)
    return JSONResponse({"status": "ok"})


@router.post("/calendar")
async def calendar_channel_webhook(
    request: Request,
    X_Goog_Channel_ID: str = Header(default=None, alias="X-Goog-Channel-ID"),
    X_Goog_Resource_ID: str = Header(default=None, alias="X-Goog-Resource-ID"),
) -> JSONResponse:
    """Handle Google Calendar channel notifications."""
    logger.info(
        "Calendar push received: channel_id=%s resource_id=%s",
        X_Goog_Channel_ID,
        X_Goog_Resource_ID,
    )
    body = await request.body()
    watcher = CalendarWatcher()
    await watcher.handle_push(headers=dict(request.headers), body=body)
    return JSONResponse({"status": "ok"})
