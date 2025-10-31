"""Prompt loading utilities"""

from pathlib import Path


def load_prompt(filename: str, **kwargs) -> str:
    """Load and format a prompt file with variables.

    Args:
        filename: Name of the prompt file (e.g., 'intro_agent.txt')
        **kwargs: Format variables for the template

    Returns:
        Formatted prompt string
    """
    prompt_path = Path(__file__).parent / filename
    prompt = prompt_path.read_text()
    return prompt.format(**kwargs)
