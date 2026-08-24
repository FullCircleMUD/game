"""
LLM-powered name generation for unique crafted items.

Naming is decoration, so nothing here is allowed to fail the craft that
asked for it. Every path — the model being down, rate-limited, disabled in
settings, or answering with a paragraph — ends in a usable name.

Callers must run this off the reactor thread. It makes a network request,
and the reactor cannot wait on one. See src/game/CLAUDE.md § Non-blocking
LLM NPC calls.
"""

import re

from evennia.utils import logger

from llm.prompt_loader import render_prompt


# What a name may contain: letters, spaces, apostrophes and hyphens. Names
# come back as raw model output, so this is the gate, not a tidy-up.
_ALLOWED = re.compile(r"^[A-Za-z][A-Za-z'\- ]*$")

_MAX_WORDS = 2
_MAX_LENGTH = 32


class ItemNameGenerator:
    """LLM-powered name generation for unique crafted items."""

    def generate_inset_name(self, weapon_name, gem_effects, character):
        """
        Generate a unique name for a gem-inset weapon.

        Args:
            weapon_name: Base weapon name (e.g. "Iron Longsword")
            gem_effects: List of effect dicts from the gem
            character: The character performing the insetting

        Returns:
            str: Generated name for the weapon, or None if the model gave
                nothing usable. The caller decides what to call it instead
                — naming must never be the reason a craft fails.
        """
        from llm.service import LLMService

        prompt = render_prompt("inset_name.md", {
            "weapon_name": weapon_name,
            "effects": self._describe_effects(gem_effects),
        })
        if not prompt:
            return None

        try:
            reply = LLMService.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=12,
                temperature=0.9,
                npc_key=f"inset:{getattr(character, 'key', 'unknown')}",
            )
        except Exception:
            logger.log_trace("inset naming: the model call failed")
            return None

        return self._clean(reply)

    @staticmethod
    def _describe_effects(gem_effects):
        """
        Turn the gem's effect dicts into something a model can name from.

        Args:
            gem_effects: list of wear_effect dicts.

        Returns:
            str: a comma-separated description, or a neutral phrase if the
                effects carry nothing readable.
        """
        described = []
        for effect in gem_effects or []:
            if not isinstance(effect, dict):
                continue
            name = effect.get("effect") or effect.get("condition")
            if name:
                described.append(str(name).replace("_", " ").lower())

        return ", ".join(described) if described else "an unnamed magic"

    @staticmethod
    def _clean(reply):
        """
        Make a model's reply safe to use as an item name, or reject it.

        Args:
            reply: whatever the model returned, possibly None.

        Returns:
            str: the cleaned name, or None if it could not be salvaged.
        """
        if not reply:
            return None

        # Models like to wrap names in quotes and end with a full stop.
        name = reply.strip().strip('"\'').strip(" .!").strip()

        if not name or len(name) > _MAX_LENGTH:
            return None
        if len(name.split()) > _MAX_WORDS:
            return None
        if not _ALLOWED.match(name):
            return None

        return name


name_generator = ItemNameGenerator()
