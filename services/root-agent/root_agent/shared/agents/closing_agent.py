"""
Closing Agent for System Design Interview

Wraps up the interview, answers questions, and provides summary.
"""

from google.adk.agents import Agent

from ..constants import MODEL_NAME
from ..prompts.prompt_loader import load_prompt

closing_agent = Agent(
    model=MODEL_NAME,
    name="closing_agent",
    description="Wraps up the interview, answers candidate questions, and provides encouragement",
    instruction=load_prompt("closing_agent.txt"),
)
