import operator
import os
from typing import Annotated, List, Sequence, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

# --- LangGraph imports ---
from langgraph.prebuilt import ToolNode
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.crud.tool import get_user_tools
from app.database.connection import get_db
from app.models.user import UserInDB

router = APIRouter()

# In-memory conversation history (user_id -> list of messages)
conversation_histories = {}

# Helper to get enabled integrations for user
INTEGRATION_PORTS = {
    "gmail": 9001,
    "calendar": 9002,
}

# Docker service names for MCP servers
MCP_SERVERS = {
    "gmail": "gmail_mcp_server",
    "calendar": "calendar_mcp_server",
}


def get_system_prompt(user_id):
    return (
        f"You are a helpful assistant with access to the user's Gmail and Calendar tools. "
        f"The current user's id is {user_id}. Always include 'user_id': {user_id} in any tool call that requires it. "
        "Use these tools to answer questions about their email and calendar. "
        "If you need to use a tool, call it directly. If you don't know the answer, say so."
    )


# --- LangGraph State Definition ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


# --- Utility: Convert history to LangChain messages ---
def convert_history_to_messages(history, user_id):
    messages = [SystemMessage(content=get_system_prompt(user_id))]
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    return messages


# --- Get MCP tools for user ---
async def get_mcp_tools_for_user(user_id, user_tools):
    mcp_servers = {}
    for tool in user_tools:
        if tool.state == "enabled" and tool.integration_name in INTEGRATION_PORTS:
            port = INTEGRATION_PORTS[tool.integration_name]
            server_name = MCP_SERVERS[tool.integration_name]
            mcp_servers[tool.integration_name] = {
                "url": f"http://{server_name}:{port}/mcp",
                "transport": "streamable_http",
            }
    if not mcp_servers:
        return None, None
    client = MultiServerMCPClient(mcp_servers)
    tools = await client.get_tools()
    return tools, client


# --- Get LLM instance ---
async def get_llm(llm_choice: str):
    if llm_choice == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        return ChatOpenAI(model="gpt-4o", api_key=api_key)
    else:  # gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite", google_api_key=api_key
        )


# --- LangGraph Node: Model call ---
def call_model_factory(llm):
    async def call_model(state: AgentState):
        messages = state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    return call_model


# --- LangGraph Node: Should continue? ---
def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    # If there are tool calls, continue; else, end
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "action"
    return END


@router.post("/message")
async def chat_message(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    print(f"Chatbot endpoint called for user: {current_user.email}")
    data = await request.json()
    user_id = current_user.id
    message = data.get("message")
    llm_choice = data.get("llm", "gemini")  # default to gemini
    print(f"Message: {message}, LLM: {llm_choice}")

    if not message:
        raise HTTPException(status_code=400, detail="Message required")

    # Initialize conversation history
    history = conversation_histories.setdefault(user_id, [])
    history.append({"role": "user", "content": message})

    # Get user's enabled tools
    user_tools = get_user_tools(db, user_id)
    print(f"User tools: {[f'{t.integration_name}:{t.tool_name}' for t in user_tools]}")

    tools, mcp_client = await get_mcp_tools_for_user(user_id, user_tools)
    if not tools:
        print("No tools available")
        return {
            "response": "No integrations enabled. Please add an integration.",
            "history": history,
        }

    print(f"Available MCP tools: {[t.name for t in tools]}")

    try:
        llm = await get_llm(llm_choice)
        # Bind tools to LLM for tool-calling
        llm = llm.bind_tools(tools)

        # --- Build LangGraph agent graph ---
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model_factory(llm))
        workflow.add_node("action", ToolNode(tools))
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent", should_continue, {"action": "action", END: END}
        )
        workflow.add_edge("action", "agent")
        app = workflow.compile()

        # Convert history to proper message format
        messages = convert_history_to_messages(history, user_id)
        state = {"messages": messages}
        # Run the agent graph (stream for robustness, collect last AI message)
        response_text = None
        async for output in app.astream(state):
            for node_output in output.values():
                for msg in node_output["messages"]:
                    if isinstance(msg, AIMessage):
                        response_text = msg.content
        if not response_text:
            response_text = (
                "Sorry, I couldn't find an answer or the tool did not return any data."
            )
        history.append({"role": "assistant", "content": response_text})
        print(f"Assistant response: {response_text}")
        return {"response": response_text, "history": history}
    except Exception as e:
        print(f"Error in chatbot processing: {e}")
        import traceback

        traceback.print_exc()
        return {"response": f"Error processing message: {e!s}", "history": history}
