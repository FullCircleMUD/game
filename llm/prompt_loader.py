"""
Prompt loader — loads and caches prompt templates from markdown files.

Templates use Python ``str.format_map()`` with named placeholders:
    {name}, {personality}, {knowledge}, {location}, etc.

Files are cached in memory after first load (cleared on server restart).
Prompt files live in ``llm/prompts/`` relative to GAME_DIR/FullCircleMUD/.
"""

import logging
import os
from functools import lru_cache

logger = logging.getLogger("llm.prompt_loader")

# Resolve prompts directory relative to this file's location
_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


@lru_cache(maxsize=32)
def load_prompt(filename):
    """
    Load a prompt template file from ``llm/prompts/``.

    Cached after first read — restart server to pick up changes.

    Args:
        filename: e.g. "roleplay_npc.md"

    Returns:
        str: The raw template text, or None if file not found.
    """
    path = os.path.join(_PROMPTS_DIR, filename)
    if not os.path.exists(path):
        logger.warning("Prompt file not found: %s", path)
        return None
    with open(path, "r") as f:
        return f.read()


def render_prompt(filename, variables):
    """
    Load a prompt template and fill in variables.

    Uses ``str.format_map()`` with a defaulting dict so missing
    variables produce ``{var_name}`` instead of raising KeyError.

    Args:
        filename: prompt file name (e.g. "roleplay_npc.md")
        variables: dict of template variables

    Returns:
        str: Rendered prompt, or None if file not found.
    """
    template = load_prompt(filename)
    if template is None:
        return None
    try:
        return template.format_map(_DefaultDict(variables))
    except Exception:
        logger.exception("Error rendering prompt %s", filename)
        return template


def clear_cache():
    """Clear the prompt cache (e.g. after editing prompt files)."""
    load_prompt.cache_clear()


class _DefaultDict(dict):
    """Dict that returns ``{key}`` for missing keys instead of raising."""

    def __missing__(self, key):
        return "{" + key + "}"
