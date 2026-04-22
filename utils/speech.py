"""
Shared language-comprehension helpers for speech commands.

Used by cmd_say / cmd_whisper / cmd_shout so the rules for "who can speak
what" and "who understands what" live in exactly one place.

Rules:
    - Common is universal.
    - Humanoid languages: speaker must have the language in db.languages;
      listener understands if they know it OR if they have COMPREHEND_LANGUAGES.
    - Animal language: speaker must have SPEAK_WITH_ANIMALS active OR have
      "animal" in db.languages (animal NPCs themselves natively know it);
      listener understands only if they have SPEAK_WITH_ANIMALS — note that
      COMPREHEND_LANGUAGES does NOT cover animal. Animal NPCs that have
      "animal" in db.languages also understand other animal speakers.
"""

from enums.condition import Condition
from enums.languages import Languages

ANIMAL = Languages.ANIMAL.value


def caller_can_speak(caller, language):
    """Return True if caller is permitted to speak the given language."""
    if language == "common":
        return True
    caller_languages = set(caller.db.languages or set())
    if language in caller_languages:
        return True
    if language == ANIMAL:
        if hasattr(caller, "has_condition") and caller.has_condition(
            Condition.SPEAK_WITH_ANIMALS
        ):
            return True
    return False


def listener_understands(listener, language):
    """Return True if listener comprehends speech in the given language."""
    if language == "common":
        return True
    listener_languages = set(getattr(listener.db, "languages", None) or set())
    if language in listener_languages:
        return True
    if language == ANIMAL:
        return hasattr(listener, "has_condition") and listener.has_condition(
            Condition.SPEAK_WITH_ANIMALS
        )
    # Comprehend Languages covers humanoid speech only — animal is gated above.
    return hasattr(listener, "has_condition") and listener.has_condition(
        Condition.COMPREHEND_LANGUAGES
    )
