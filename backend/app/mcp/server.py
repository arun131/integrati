from app.mcp.instance import mcp
from app.integrations.gmail import mcp_tools as gmail_tools
from app.integrations.calendar import mcp_tools as calendar_tools
from fastapi import Request

# Importing tool modules ensures their @mcp.tool-decorated functions
# are registered automatically when the module is imported. No manual
# registration calls are required with current fastmcp versions.

from fastapi import FastAPI, APIRouter

# Obtain FastAPI application from FastMCP instance if provided; otherwise create our own
if hasattr(mcp, "app"):
    app = mcp.app  # Older FastMCP versions expose the underlying FastAPI app
else:
    app = FastAPI(title="Integrati MCP API")
    # Newer FastMCP exposes `router` which contains its generated endpoints
    if hasattr(mcp, "router") and isinstance(mcp.router, APIRouter):
        app.include_router(mcp.router, prefix="/mcp")

# Placeholder for custom /mcp/v1/tools endpoint for per-user filtering
from fastapi import Depends
from app.core.dependencies import get_current_user
from app.models.user import UserInDB

def get_user_id_from_request(request: Request, current_user: UserInDB = Depends(get_current_user)):
    return current_user.id

from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.crud.tool import get_user_tools

@app.get('/mcp/v1/tools')
async def custom_tools_endpoint(request: Request, current_user: UserInDB = Depends(get_current_user), db: Session = Depends(get_db)):
    user_tools = get_user_tools(db, current_user.id)
    allowed_tools = [t.tool_name for t in user_tools if t.state in ('enabled', 'verify')]
    all_tools = await mcp.default_tools_endpoint(request)
    # Filter out tools not allowed for this user
    filtered_tools = [tool for tool in all_tools if tool['name'] in allowed_tools]
    return filtered_tools