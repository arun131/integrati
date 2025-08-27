"""Frontend API for tool approval management."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from mcp_plexus.plexus_auth.dependencies import get_current_plexus_user_from_token
from mcp_plexus.permissions.service import PermissionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/approvals", tags=["Tool Approvals"])


class ApprovalResponseRequest(BaseModel):
    """Request model for approval responses."""

    reason: str = ""
    base_config_token: str = None


@router.get("/pending")
async def get_pending_approvals(
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
) -> Dict[str, Any]:
    """Get pending approval requests for user."""
    try:
        permission_service = PermissionService()

        pending_requests = await permission_service.get_pending_approvals(
            entity_id=current_user["entity_id"], approving_config_id="base"
        )

        return {"pending_approvals": pending_requests, "count": len(pending_requests)}

    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pending approvals",
        )


@router.post("/approve/{approval_id}")
async def approve_request(
    approval_id: str,
    request_data: ApprovalResponseRequest,
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
) -> Dict[str, Any]:
    """Approve and execute tool request."""
    try:
        permission_service = PermissionService()

        # Use the provided base config token for execution
        base_config_token = request_data.base_config_token
        if not base_config_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Base config token required for approval execution",
            )

        success = await permission_service.approve_request(
            approval_id=approval_id,
            approver_entity_id=current_user["entity_id"],
            base_config_token=base_config_token,
            reason=request_data.reason,
        )

        if success:
            return {
                "success": True,
                "message": "Request approved and executed successfully",
                "approval_id": approval_id,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found or already processed",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve request",
        )


@router.get("/history")
async def get_approval_history(
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
) -> Dict[str, Any]:
    """Get approval history for user."""
    try:
        permission_service = PermissionService()

        history_requests = await permission_service.get_approval_history(
            entity_id=current_user["entity_id"], approving_config_id="base"
        )

        return {"approval_history": history_requests, "count": len(history_requests)}

    except Exception as e:
        logger.error(f"Error getting approval history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve approval history",
        )


@router.post("/deny/{approval_id}")
async def deny_request(
    approval_id: str,
    request_data: ApprovalResponseRequest,
    current_user: Dict[str, Any] = Depends(get_current_plexus_user_from_token),
) -> Dict[str, Any]:
    """Deny tool request."""
    try:
        permission_service = PermissionService()

        success = await permission_service.deny_request(
            approval_id=approval_id,
            approver_entity_id=current_user["entity_id"],
            reason=request_data.reason,
        )

        if success:
            return {
                "success": True,
                "message": "Request denied successfully",
                "approval_id": approval_id,
                "reason": request_data.reason,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found or already processed",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error denying request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deny request",
        )
