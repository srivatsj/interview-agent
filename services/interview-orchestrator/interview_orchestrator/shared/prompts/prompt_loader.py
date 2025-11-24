"""Prompt loading utilities"""

import os
from pathlib import Path


def load_prompt(filename: str, **kwargs) -> str:
    """Load and format a prompt file with variables.

    Args:
        filename: Name of the prompt file (e.g., 'intro_agent.txt')
        **kwargs: Format variables for the template

    Returns:
        Formatted prompt string
    """
    # Select dev or prod folder based on ENV variable
    env = os.getenv("ENV", "dev").lower()
    folder = "dev" if env != "prod" else "prod"

    prompt_path = Path(__file__).parent / folder / filename
    prompt = prompt_path.read_text()
    return prompt.format(**kwargs)
