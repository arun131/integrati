# Gmail Integration Tool Development Guide

This guide provides comprehensive instructions for creating new Gmail integration tools following standardized patterns and best practices.

## Table of Contents
1. [Function Structure](#function-structure)
2. [Decorators](#decorators)
3. [Permission Handling](#permission-handling)
4. [Response Format Standardization](#response-format-standardization)
5. [Docstring Format](#docstring-format)
6. [Error Handling](#error-handling)
7. [Constants File Updates](#constants-file-updates)
8. [Testing Checklist](#testing-checklist)

## Function Structure

All Gmail tools should follow this standardized structure:

```python
@staticmethod
@PLEXUS_SERVER_INSTANCE.tool()
async def tool_name(
    ctx: FastMCPBaseContext,
    param1: Type,
    param2: Optional[Type] = None,
) -> ReturnType:
    """Comprehensive docstring following the format below."""
    try:
        # 1. Extract context
        plexus_ctx = PlexusContext(ctx.fastmcp)
        entity_id = plexus_ctx.entity_id
        user_id = getattr(plexus_ctx, "user_id", None)

        # 2. Validate user context
        if not user_id:
            raise ToolError("User ID not available in context")

        # 3. Handle permissions using PermissionHelper
        permission_result = await PermissionHelper.check_and_handle_permissions(
            entity_id=entity_id,
            user_id=user_id,
            tool_name="tool_name",
            tool_params={
                "param1": param1,
                "param2": param2,
            },
            no_access_response=standardized_no_access_response,
            restricted_access_response=standardized_restricted_response,
            approval_message="Custom approval message for restricted access",
            integration_type="gmail",
        )

        if permission_result is not None:
            return permission_result

        # 4. Execute tool logic
        gmail_api = GmailAPI(entity_id, user_id)
        # ... tool implementation ...

        # 5. Return standardized success response
        return standardized_success_response

    except PlexusExternalAuthRequiredError:
        raise ToolError("Gmail integration not authenticated. Please add Gmail integration first.")
    except Exception as e:
        logger.error(f"Error in tool_name: {e}")
        raise ToolError(f"Error description: {str(e)}")
```

## Decorators

Always use these decorators in this exact order:

```python
@staticmethod
@PLEXUS_SERVER_INSTANCE.tool()
```

## Permission Handling

### Using PermissionHelper (RECOMMENDED)

```python
permission_result = await PermissionHelper.check_and_handle_permissions(
    entity_id=entity_id,
    user_id=user_id,
    tool_name="your_tool_name",
    tool_params={
        "param1": param1,
        "param2": param2,
    },
    no_access_response={
        # Return same structure as success case
        "status": "access_denied",
        "status_message": "You don't have permission to perform this action.",
        # Include other fields that would be in success response
    },
    restricted_access_response={
        # Return same structure as success case
        "status": "approval_required",
        "status_message": "The tool request with details {'param1': 'value'} is sent to the user and they can approve it on the app.",
        # Include other fields that would be in success response
    },
    approval_message="Your request to [action description] was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
    integration_type="gmail",
)

if permission_result is not None:
    return permission_result
```

### Response Format Requirements

All functions must return responses with consistent structure:

#### Success Response
```python
{
    "status": "success",  # Always "success" for successful operations
    "status_message": "success",  # Always "success" for successful operations
    # ... other tool-specific fields
}
```

#### No Access Response
```python
{
    "status": "access_denied",
    "status_message": "You don't have permission to perform this action.",
    # ... other fields matching success response structure
}
```

#### Restricted Access Response
```python
{
    "status": "approval_required",
    "status_message": "The tool request with details {'key': 'value'} is sent to the user and they can approve it on the app.",
    # ... other fields matching success response structure
}
```

## Docstring Format

Use comprehensive docstrings with this exact format:

```python
"""Brief description of what the function does.

Detailed explanation of the function's purpose, behavior, and requirements.
Mention any special considerations or limitations.

Args:
    param1: Description of parameter 1 and its expected format.
    param2: Description of parameter 2. Optional if it has a default.

Returns:
    Dict containing:
    - field1: Description of field1
    - field2: Description of field2
    - status_message: Operation status ("success", "access_denied", or approval message)
"""
```

## Error Handling

### Standard Error Handling Pattern

```python
try:
    # Tool implementation
    pass
except PlexusExternalAuthRequiredError:
    raise ToolError(
        "Gmail integration not authenticated. Please add Gmail integration first."
    )
except Exception as e:
    logger.error(f"Error in tool_name: {e}")
    raise ToolError(f"Error description: {str(e)}")
```

### Common Error Types

1. **PlexusExternalAuthRequiredError**: Authentication required
2. **ToolError**: All other tool-specific errors
3. **ValueError**: Invalid parameter values
4. **Exception**: Generic fallback

## Constants File Updates

### 1. Update GMAIL_TOOL_NAMES list

Add your new tool name to the list:

```python
GMAIL_TOOL_NAMES = [
    # ... existing tools ...
    "your_new_tool_name",
]
```

### 2. Update GMAIL_DEFAULT_BACKGROUND_PERMISSIONS

Add permission level for your tool:

```python
GMAIL_DEFAULT_BACKGROUND_PERMISSIONS = {
    # ... existing permissions ...
    "your_new_tool_name": permission_level,  # 1=NO_ACCESS, 2=RESTRICTED_ACCESS, 3=FULL_ACCESS
}
```

### Permission Level Guidelines

- **3 (FULL_ACCESS)**: Read-only operations, safe for background use
- **2 (RESTRICTED_ACCESS)**: Write/modify operations requiring approval
- **1 (NO_ACCESS)**: Dangerous operations, always blocked

## Testing Checklist

Before submitting your tool, ensure:

### ✅ Function Structure
- [ ] Uses correct decorators (`@staticmethod` and `@PLEXUS_SERVER_INSTANCE.tool()`)
- [ ] Follows async/await pattern
- [ ] Has proper type hints
- [ ] Uses PlexusContext correctly

### ✅ Permission Handling
- [ ] Uses PermissionHelper.check_and_handle_permissions
- [ ] Provides standardized no_access_response
- [ ] Provides standardized restricted_access_response
- [ ] Includes descriptive approval_message
- [ ] Handles permission_result correctly

### ✅ Response Format
- [ ] Success responses include `"status": "success"` and `"status_message": "success"`
- [ ] All response types have consistent structure
- [ ] Restricted access includes approval message format
- [ ] No access includes permission denied message

### ✅ Documentation
- [ ] Comprehensive docstring with Args and Returns sections
- [ ] Clear parameter descriptions
- [ ] Detailed return value specifications
- [ ] Usage examples where helpful

### ✅ Error Handling
- [ ] Handles PlexusExternalAuthRequiredError correctly
- [ ] Logs errors appropriately
- [ ] Raises ToolError for all error cases
- [ ] Provides meaningful error messages

### ✅ Constants Updates
- [ ] Added to GMAIL_TOOL_NAMES list
- [ ] Added to GMAIL_DEFAULT_BACKGROUND_PERMISSIONS with appropriate level
- [ ] Comments explain permission choices

### ✅ Code Quality
- [ ] No linter errors
- [ ] Follows existing code patterns
- [ ] Meaningful variable names
- [ ] Appropriate comments for complex logic

## Example: Complete Tool Implementation

```python
@staticmethod
@PLEXUS_SERVER_INSTANCE.tool()
async def archive_email(
    ctx: FastMCPBaseContext,
    message_id: str,
    remove_labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Archive a Gmail message by removing INBOX label and optionally other labels.

    This function removes the specified message from the inbox and can optionally
    remove additional labels. Requires write permissions for Gmail operations.

    Args:
        message_id: Gmail message ID to archive
        remove_labels: Optional list of additional label names to remove

    Returns:
        Dict containing:
        - message_id: ID of the archived message
        - labels_removed: List of labels that were removed
        - status: Operation status ("success", "access_denied", "approval_required")
        - status_message: Human-readable status message
    """
    try:
        plexus_ctx = PlexusContext(ctx.fastmcp)
        entity_id = plexus_ctx.entity_id
        user_id = getattr(plexus_ctx, "user_id", None)

        if not user_id:
            raise ToolError("User ID not available in context")

        permission_result = await PermissionHelper.check_and_handle_permissions(
            entity_id=entity_id,
            user_id=user_id,
            tool_name="archive_email",
            tool_params={
                "message_id": message_id,
                "remove_labels": remove_labels,
            },
            no_access_response={
                "message_id": message_id,
                "labels_removed": [],
                "status": "access_denied",
                "status_message": "You don't have permission to archive emails with this configuration.",
            },
            restricted_access_response={
                "message_id": message_id,
                "labels_removed": [],
                "status": "approval_required",
                "status_message": f"The tool request with details {{'message_id': '{message_id}'}} is sent to the user and they can approve it on the app.",
            },
            approval_message=f"Your request to archive email '{message_id}' was received but you have restricted access to this tool so the request is sent to the user for final approval on the app.",
            integration_type="gmail",
        )

        if permission_result is not None:
            return permission_result

        gmail_api = GmailAPI(entity_id, user_id)
        result = await gmail_api.archive_email(message_id, remove_labels)

        return {
            "message_id": message_id,
            "labels_removed": result.get("labels_removed", []),
            "status": "success",
            "status_message": "success",
        }
    except PlexusExternalAuthRequiredError:
        raise ToolError(
            "Gmail integration not authenticated. Please add Gmail integration first."
        )
    except Exception as e:
        logger.error(f"Error archiving email: {e}")
        raise ToolError(f"Error archiving email: {str(e)}")
```

## Integration Checklist

After implementing your tool:

1. [ ] Update `constants.py` with new tool name and permissions
2. [ ] Test all permission scenarios (full access, restricted, no access)
3. [ ] Verify response format consistency
4. [ ] Test error handling scenarios
5. [ ] Run linter and fix any issues
6. [ ] Add tool to any relevant documentation
7. [ ] Test integration with frontend approval flow (for restricted tools)

Remember: Consistency is key! All tools should follow the same patterns for maintainability and user experience.</contents>
</xai:function_call">Create a comprehensive tool development guide
