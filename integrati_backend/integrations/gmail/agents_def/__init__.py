"""Gmail agent definitions package."""

from .signature import GmailAgentSignature
from .agent import get_gmail_agent, GmailAgent

__all__ = ["GmailAgentSignature", "GmailAgent", "get_gmail_agent"]
