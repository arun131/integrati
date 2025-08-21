"""
Main chatbot processing function that implements the simplified approach with fresh MCP connections.
"""

import dspy
import logging
import os
from datetime import datetime
from typing import Dict, Any, List
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .conversation_manager import ConversationManager

logger = logging.getLogger(__name__)

# Global DSPy configuration - configure once at module level
_dspy_configured = False

# Tool name constants for categorization
# Use fallback constants to avoid circular import issues during testing
GMAIL_TOOL_NAMES = [
    "gmail",
    "email",
    "mail",
    "search_gmail_messages",
    "get_last_received_email",
    "send_gmail_message",
    "get_gmail_message",
    "get_unread_email_count",
    "search_gmail_by_sender",
    "search_gmail_by_subject",
]
CALENDAR_TOOL_NAMES = [
    "calendar",
    "event",
    "schedule",
    "create_calendar_event",
    "get_calendar_events",
    "update_calendar_event",
    "delete_calendar_event",
]
COMMON_TOOL_NAMES = [
    "add",
    "subtract",
    "multiply",
    "divide",
    "calculate",
    "add_numbers",
    "sum_list",
]


def configure_dspy_once():
    """Configure DSPy once at module level to avoid async task configuration errors."""
    global _dspy_configured
    if _dspy_configured:
        return True

    try:
        # Try to configure DSPy with available API keys
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if gemini_api_key:
            dspy.configure(
                lm=dspy.LM("gemini/gemini-2.0-flash-lite", api_key=gemini_api_key),
                max_tokens=5000,
                temperature=0.1,
            )
            logger.info("DSPy configured with Gemini LLM")
            _dspy_configured = True
            return True
        elif openai_api_key:
            dspy.configure(
                lm=dspy.LM("gpt-4o-mini", api_key=openai_api_key),
                max_tokens=5000,
                temperature=0.1,
            )
            logger.info("DSPy configured with OpenAI LLM")
            _dspy_configured = True
            return True
        else:
            logger.error(
                "No LLM API key configured. Please set GEMINI_API_KEY or OPENAI_API_KEY"
            )
            return False
    except Exception as e:
        logger.error(f"Failed to configure DSPy: {e}")
        return False


class DSPyOrchestrator(dspy.Signature):
    """
    You are an orchestrator agent that delegates tasks to specialized sub-agents.
    If the task is simple enough, you can use the basic tools directly to respond to the user
    without invoking a subagent.

    You are given:
    - A list of basic tools
    - A set of available subagents (e.g., Gmail, Calendar)
    - The historical chat context

    Focus most on fulfilling the user's request effectively.
    """

    user_query: str = dspy.InputField(desc="The user's query to be processed")
    historical_context: dict = dspy.InputField(
        desc="Chat history with the user for the current session"
    )
    available_subagents: list[str] = dspy.InputField(
        desc="The list of subagents available to the orchestrator"
    )
    current_time: str = dspy.InputField(
        desc="The current time in the format of YYYY-MM-DD HH:MM:SS"
    )

    tools_used: list[str] = dspy.OutputField(
        desc="The list of tools used by you and the subagents to fulfill the request. The agents are not considered tools."
    )
    reasoning: str = dspy.OutputField(desc="The reasoning process of the orchestrator")
    response: str = dspy.OutputField(desc="The response to the user's query")


class GmailAgent(dspy.Signature):
    """
    You are a Gmail agent that can handle the user's Gmail-related requests.
    You are given Gmail-specific tools and must decide which to use to fulfill the request.
    """

    user_query: str = dspy.InputField(desc="The user's Gmail-related query")
    request_context: dict = dspy.InputField(desc="Context passed from the orchestrator")

    tools_used: list[str] = dspy.OutputField(
        desc="The Gmail tools used to fulfill the request"
    )
    reasoning: str = dspy.OutputField(desc="The reasoning process of the Gmail agent")
    response: str = dspy.OutputField(desc="The Gmail-related response to the query")


class CalendarAgent(dspy.Signature):
    """
    You are a Calendar agent that can handle the user's calendar-related requests.
    You are given Calendar-specific tools and must decide which to use to fulfill the request.
    """

    user_query: str = dspy.InputField(desc="The user's Calendar-related query")
    request_context: dict = dspy.InputField(desc="Context passed from the orchestrator")

    tools_used: list[str] = dspy.OutputField(
        desc="The Calendar tools used to fulfill the request"
    )
    reasoning: str = dspy.OutputField(
        desc="The reasoning process of the Calendar agent"
    )
    response: str = dspy.OutputField(desc="The Calendar-related response to the query")


async def create_fresh_mcp_connection(tenant_id: str, token: str):
    """Create a fresh MCP connection for each request."""
    mcp_backend_url = os.getenv("MCP_BACKEND_URL", "http://localhost:8000")
    url = f"{mcp_backend_url}/mcp/{tenant_id}"

    try:
        # Create the connection and session
        stream = streamablehttp_client(
            url, headers={"Authorization": f"Bearer {token}"}
        )
        (read, write, _) = await stream.__aenter__()
        session = ClientSession(read, write)
        await session.__aenter__()
        await session.initialize()
        tools_result = await session.list_tools()
        logger.info(f"Connected to MCP server for tenant {tenant_id}")
        return tools_result.tools, session, stream
    except Exception as e:
        logger.error(f"Failed to connect to MCP server for tenant {tenant_id}: {e}")
        return [], None, None


def categorize_tools_smart(tools: List[Any]) -> Dict[str, List[Any]]:
    """Categorize tools into common, Gmail, and Calendar groups."""
    # Use module-level constants defined above
    categorized = {"common": [], "gmail": [], "calendar": []}

    for tool in tools:
        tool_name = tool.name.lower()

        # Check against imported tool name lists
        if GMAIL_TOOL_NAMES and any(
            gmail_name.lower() in tool_name for gmail_name in GMAIL_TOOL_NAMES
        ):
            categorized["gmail"].append(tool)
        elif CALENDAR_TOOL_NAMES and any(
            calendar_name.lower() in tool_name for calendar_name in CALENDAR_TOOL_NAMES
        ):
            categorized["calendar"].append(tool)
        elif COMMON_TOOL_NAMES and any(
            common_name.lower() in tool_name for common_name in COMMON_TOOL_NAMES
        ):
            categorized["common"].append(tool)
        else:
            # Default to common if no match found
            categorized["common"].append(tool)

    return categorized


def make_subagents_as_tools(agents: dict[str, dspy.ReAct]):
    """Wrap subagents as callable DSPy tools so the orchestrator can invoke them."""
    subagent_tools = []
    logger.info(f"make_subagents_as_tools called with agents: {list(agents.keys())}")

    for agent_name, agent in agents.items():
        logger.info(f"Processing agent: {agent_name}, type: {type(agent)}")

        if agent is None:
            logger.info(f"Skipping {agent_name} - agent is None")
            continue  # skip missing subagents

        if "gmail" in agent_name.lower():

            async def gmail_agent_tool(
                user_query: str,
                request_context: dict,
            ):
                """Use this tool to delegate the request to the Gmail subagent."""
                return await agents["gmail_agent"].acall(
                    user_query=user_query, request_context=request_context
                )

            subagent_tools.append(gmail_agent_tool)

        elif "calendar" in agent_name.lower():

            async def calendar_agent_tool(
                user_query: str,
                request_context: dict,
            ):
                """Use this tool to delegate the request to the Calendar subagent."""
                return await agents["calendar_agent"].acall(
                    user_query=user_query, request_context=request_context
                )

            subagent_tools.append(calendar_agent_tool)

    logger.info(f"Returning {len(subagent_tools)} subagent tools")
    return subagent_tools


async def process_chatbot_request(
    chat_id: str,
    tenant_id: str,
    user_query: str,
    integrations: List[str],
    token: str,
    conversation_manager: ConversationManager,
    historical_context: dict = None,
):
    """Main chatbot processing function with fresh MCP connections and conversation history."""
    try:
        # Configure DSPy once at module level, then use context for subsequent calls
        if not configure_dspy_once():
            return {
                "success": False,
                "error": "No LLM API key configured. Please set GEMINI_API_KEY or OPENAI_API_KEY",
                "agent_used": "orchestrator",
                "tools_used": [],
                "reasoning": "LLM not configured - cannot process request",
            }

        # Use dspy.context() for this async task to avoid configuration errors
        with dspy.context():
            # 1. Get conversation history from Redis
            conversation_history = await conversation_manager.get_conversation_history(
                chat_id
            )

            # 2. Create fresh MCP connection (reconnect every time)
            logger.info("Creating fresh MCP connection...")
            mcp_tools, mcp_session, mcp_stream = await create_fresh_mcp_connection(
                tenant_id, token
            )

            if not mcp_tools or not mcp_session:
                logger.error("Failed to create MCP connection or session")
                return {
                    "success": False,
                    "error": "Failed to establish MCP connection",
                    "agent_used": "orchestrator",
                    "tools_used": [],
                    "reasoning": "MCP connection failed - cannot process request",
                }

            logger.info(
                f"MCP connection established successfully with {len(mcp_tools)} tools"
            )

            # 3. Categorize tools using smart categorization
            logger.info(f"Total MCP tools available: {len(mcp_tools)}")
            for tool in mcp_tools:
                logger.info(f"MCP tool: {tool.name} - {tool.description}")

            categorized_tools = categorize_tools_smart(mcp_tools)
            logger.info(
                f"Tool categorization - Common: {len(categorized_tools['common'])}, Gmail: {len(categorized_tools['gmail'])}, Calendar: {len(categorized_tools['calendar'])}"
            )

            # 4. Convert MCP tools to DSPy tools
            common_dspy_tools = [
                dspy.Tool.from_mcp_tool(mcp_session, tool)
                for tool in categorized_tools["common"]
            ]

            gmail_dspy_tools = [
                dspy.Tool.from_mcp_tool(mcp_session, tool)
                for tool in categorized_tools["gmail"]
            ]

            calendar_dspy_tools = [
                dspy.Tool.from_mcp_tool(mcp_session, tool)
                for tool in categorized_tools["calendar"]
            ]

            logger.info(
                f"DSPy tools created - Common: {len(common_dspy_tools)}, Gmail: {len(gmail_dspy_tools)}, Calendar: {len(calendar_dspy_tools)}"
            )

            # 5. Create subagents using the appropriate tools
            agents = {}
            if "gmail" in integrations and gmail_dspy_tools:
                agents["gmail_agent"] = dspy.ReAct(
                    signature=GmailAgent, tools=gmail_dspy_tools
                )
                logger.info(f"Created Gmail agent with {len(gmail_dspy_tools)} tools")
            else:
                logger.info(
                    f"No Gmail agent created - integrations: {integrations}, gmail_tools: {len(gmail_dspy_tools) if gmail_dspy_tools else 0}"
                )

            if "calendar" in integrations and calendar_dspy_tools:
                agents["calendar_agent"] = dspy.ReAct(
                    signature=CalendarAgent, tools=calendar_dspy_tools
                )
                logger.info(
                    f"Created Calendar agent with {len(calendar_dspy_tools)} tools"
                )
            else:
                logger.info(
                    f"No Calendar agent created - integrations: {integrations}, calendar_tools: {len(calendar_dspy_tools) if calendar_dspy_tools else 0}"
                )

            # 6. Wrap as callable subagent tools
            logger.info(f"Creating subagent tools from agents: {list(agents.keys())}")
            subagent_tools = make_subagents_as_tools(agents)
            logger.info(f"Created {len(subagent_tools)} subagent tools")

            # 7. Create the orchestrator agent
            orchestrator_agent = dspy.ReAct(
                signature=DSPyOrchestrator, tools=common_dspy_tools + subagent_tools
            )

            # 8. Create the historical context for the orchestrator
            if historical_context is None:
                historical_context = {"history_of_messages": conversation_history}
            else:
                historical_context["history_of_messages"] = conversation_history

            history = dspy.History(messages=historical_context["history_of_messages"])

            # 9. Execute the orchestrator
            logger.info("Executing orchestrator agent with MCP session...")
            response = await orchestrator_agent.acall(
                user_query=user_query,
                historical_context=history,
                available_subagents=integrations,
                current_time=datetime.now().isoformat(),
            )
            logger.info("Orchestrator agent execution completed successfully")

            # 10. Save updated conversation history to Redis (permanent storage)
            # Convert trajectory to string for reliable serialization
            trajectory_data = getattr(response, "trajectory", {})
            trajectory_string = str(trajectory_data)

            await conversation_manager.add_message_to_history(
                chat_id,
                {
                    "trajectory": trajectory_string,
                    "reasoning": response.reasoning,
                    "tools_used": response.tools_used,
                    "response": response.response,
                    "response_timestamp": datetime.now().isoformat(),
                    "user_query": user_query,
                },
            )

            # 11. Update conversation metadata
            await conversation_manager.update_conversation_metadata(
                chat_id, tenant_id, integrations
            )

            result = {
                "success": True,
                "response": response.response,
                "agent_used": "orchestrator",
                "tools_used": response.tools_used,
                "reasoning": response.reasoning,
                "trajectory": str(getattr(response, "trajectory", {})),
                "chat_id": chat_id,
                "tenant_id": tenant_id,
                "updated_history": conversation_history,
            }

            return result

    except Exception as e:
        logger.error(f"Failed to process chatbot request: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "agent_used": "orchestrator",
            "tools_used": [],
            "reasoning": f"Error occurred: {str(e)}",
        }
    finally:
        # Clean up MCP session and stream
        if "mcp_session" in locals() and mcp_session:
            try:
                await mcp_session.__aexit__(None, None, None)
                logger.info("MCP session closed successfully")
            except Exception as e:
                logger.error(f"Error closing MCP session: {e}")

        if "mcp_stream" in locals() and mcp_stream:
            try:
                await mcp_stream.__aexit__(None, None, None)
                logger.info("MCP stream closed successfully")
            except Exception as e:
                logger.error(f"Error closing MCP stream: {e}")
