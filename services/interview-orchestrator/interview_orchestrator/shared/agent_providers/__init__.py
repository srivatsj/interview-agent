"""Agent providers for interview orchestration.

This module contains client implementations for both local and remote interview agents.
"""

from .local_provider import LocalAgentProvider
from .protocol import InterviewAgentProtocol
from .registry import AgentProviderRegistry
from .remote_provider import RemoteAgentProvider

__all__ = [
    "InterviewAgentProtocol",
    "LocalAgentProvider",
    "RemoteAgentProvider",
    "AgentProviderRegistry",
]
