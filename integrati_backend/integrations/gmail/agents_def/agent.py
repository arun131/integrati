"""Gmail agent factory functions."""

import dspy
from .signature import GmailAgentSignature, GmailBackgroundAgentSignature
from typing import Literal


class GmailAgent(dspy.Module):
    """Gmail agent"""

    def __init__(self, gmail_tools: list):
        self.gmail_tools = gmail_tools
        self.agent = dspy.ReAct(signature=GmailAgentSignature, tools=gmail_tools)

    def forward(self, user_query: str, request_context: dict) -> str:
        """Forward the request to the Gmail agent."""
        return self.agent(user_query=user_query, request_context=request_context)

    async def aforward(self, user_query: str, request_context: dict) -> str:
        """Forward the request to the Gmail agent."""
        return await self.agent.acall(
            user_query=user_query, request_context=request_context
        )


class GmailBackgroundAgent(dspy.Module):
    """Gmail background agent"""

    def __init__(self, gmail_tools: list):
        self.gmail_tools = gmail_tools
        self.agent = dspy.ReAct(
            signature=GmailBackgroundAgentSignature, tools=gmail_tools
        )

    def forward(self, event_details: dict, user_context: dict) -> str:
        """Forward the request to the Gmail background agent."""
        return self.agent(event_details=event_details, user_context=user_context)

    async def aforward(self, event_details: dict, user_context: dict) -> str:
        """Forward the request to the Gmail background agent."""
        return await self.agent.acall(
            event_details=event_details, user_context=user_context
        )


def get_gmail_agent(
    gmail_tools: list, trigger: Literal["background", "chatbot"]
) -> GmailAgent:
    """
    Create and return a Gmail agent with the provided tools.
    Args:
        gmail_tools: List of DSPy tools for Gmail operations
        trigger: The trigger for the Gmail agent. Can be "background" or "chatbot"
    Returns:
        GmailAgent: Configured Gmail agent
    """
    if trigger == "background":
        agent = GmailBackgroundAgent(gmail_tools)
    else:
        agent = GmailAgent(gmail_tools)
    return agent
