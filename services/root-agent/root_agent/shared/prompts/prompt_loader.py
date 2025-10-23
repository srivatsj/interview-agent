"""Prompt loading utilities"""

from pathlib import Path

from ..constants import SUPPORTED_COMPANIES, SUPPORTED_INTERVIEW_TYPES


def load_prompt(filename: str, **kwargs) -> str:
    """Load and format a prompt file with variables.

    Args:
        filename: Name of the prompt file (e.g., 'routing_agent.txt')
        **kwargs: Additional format variables

    Returns:
        Formatted prompt string
    """
    prompt_path = Path(__file__).parent / filename
    prompt = prompt_path.read_text()

    # Default variables
    defaults = {
        "companies": ", ".join(SUPPORTED_COMPANIES),
        "interview_types": ", ".join(SUPPORTED_INTERVIEW_TYPES),
    }

    # Merge with provided kwargs
    format_vars = {**defaults, **kwargs}

    return prompt.format(**format_vars)
