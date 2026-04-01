"""
PlayerPreferencesMixin — persistent per-player display/UI preferences.

Mix into FCMCharacter to add toggleable boolean preferences (brief mode,
auto-exits, reactive spells, etc.).  New preferences require only an
AttributeProperty and a PREFERENCES registry entry — the ``toggle``
command reads the registry automatically.

Gated preferences (e.g. reactive spells) can include a ``gate`` callable
and ``gate_fail`` message.  The gate is checked before toggling and
before displaying the preference — players only see preferences they
have access to.

Usage:
    class FCMCharacter(PlayerPreferencesMixin, ...):
        pass

    # In-game:
    #   toggle              — show all preferences
    #   toggle brief        — flip brief mode on/off
    #   toggle smite        — flip reactive smite on/off (if memorised)
    #   toggle shield       — flip reactive shield on/off (if memorised)
    #   toggle nofollow     — block/allow others from following you
"""

from evennia.typeclasses.attributes import AttributeProperty


class PlayerPreferencesMixin:
    """Toggleable boolean preferences for player characters.

    To add a new preference:
        1. Add an ``AttributeProperty`` on this class.
        2. Add an entry to ``PREFERENCES`` mapping a user-facing name
           to the attribute name and a short description.
        3. (Optional) Add ``gate`` and ``gate_fail`` for gated prefs.
    """

    # ── Preference attributes ──────────────────────────────────────────
    brief_mode = AttributeProperty(False, autocreate=False)
    auto_exits = AttributeProperty(True, autocreate=False)
    # nofollow is defined in FollowableMixin
    afk = AttributeProperty(False, autocreate=False)
    smite_active = AttributeProperty(False, autocreate=False)
    shield_active = AttributeProperty(False, autocreate=False)

    # ── Registry ───────────────────────────────────────────────────────
    # Keys are the names players type (e.g. ``toggle brief``).
    # Optional ``gate``: callable(char) → bool. If False, toggle is blocked.
    # Optional ``gate_fail``: message shown when gate fails.
    PREFERENCES = {
        "afk": {
            "attr": "afk",
            "desc": "Mark yourself as away from keyboard",
        },
        "brief": {
            "attr": "brief_mode",
            "desc": "Skip room descriptions on movement",
        },
        "autoexit": {
            "attr": "auto_exits",
            "desc": "Show exits automatically in room display",
        },
        "nofollow": {
            "attr": "nofollow",
            "desc": "Prevent others from following you",
        },
        "smite": {
            "attr": "smite_active",
            "desc": "Auto-trigger Smite on weapon hits (costs mana)",
            "gate": lambda char: (
                hasattr(char, "is_memorised") and char.is_memorised("smite")
            ),
            "gate_fail": "You don't have Smite memorised.",
        },
        "shield": {
            "attr": "shield_active",
            "desc": "Auto-trigger Shield when attacked (costs mana)",
            "gate": lambda char: (
                hasattr(char, "is_memorised") and char.is_memorised("shield")
            ),
            "gate_fail": "You don't have Shield memorised.",
        },
    }

    # ── Helpers ────────────────────────────────────────────────────────

    def _passes_gate(self, entry):
        """Check if a preference's gate allows access."""
        gate = entry.get("gate")
        return gate is None or gate(self)

    def toggle_preference(self, pref_name):
        """Toggle a boolean preference by its registry name.

        Args:
            pref_name (str): Key in ``PREFERENCES`` (case-insensitive).

        Returns:
            tuple[str, bool]: ``(display_name, new_value)`` on success.
            tuple[None, str]: ``(None, fail_message)`` if gate blocks.
            None: if *pref_name* is not recognised.
        """
        key = pref_name.lower()
        entry = self.PREFERENCES.get(key)
        if entry is None:
            return None
        if not self._passes_gate(entry):
            return None, entry.get("gate_fail", "You can't toggle that.")
        attr = entry["attr"]
        new_val = not getattr(self, attr, False)
        setattr(self, attr, new_val)
        return key, new_val

    def get_preference_display(self):
        """Return a formatted table of all preferences and current values.

        Gated preferences that the player doesn't qualify for are hidden.

        Returns:
            str: Multi-line string ready to send to the player.
        """
        lines = ["|wPreferences|n"]
        for name, entry in self.PREFERENCES.items():
            if not self._passes_gate(entry):
                continue
            val = getattr(self, entry["attr"], False)
            status = "|gON|n" if val else "|rOFF|n"
            lines.append(f"  {name:<12} {status:<16} {entry['desc']}")
        return "\n".join(lines)
