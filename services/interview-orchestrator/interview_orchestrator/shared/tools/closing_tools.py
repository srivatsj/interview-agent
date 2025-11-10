"""Tools for interview closing phase.

Marks interview as complete.
"""

from google.adk.tools import ToolContext


def mark_interview_complete(tool_context: ToolContext) -> str:
    """Mark the entire interview as complete and end the session.

    Call this tool when you have:
    1. Thanked the candidate for their time
    2. Answered all their questions (or confirmed they have none)
    3. Provided encouraging closing remarks
    4. Explained next steps if applicable

    Returns:
        Confirmation message
    """
    tool_context.state["interview_complete"] = True
    tool_context.state["interview_phase"] = "done"

    return "Interview marked as complete. Thank you for using the interview system!"
