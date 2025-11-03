"""Plugins for ADK Runner.

Plugins provide global cross-cutting concerns like logging, metrics, and monitoring.
They execute before agent callbacks and can short-circuit execution.
"""

from .logging_plugin import LoggingPlugin

__all__ = ["LoggingPlugin"]
