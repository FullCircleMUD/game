"""
AnimalSpeakerMixin — composable mixin for animal NPCs that vocalise / speak.

Apply to any NPC that should produce species-appropriate vocalisations in
response to events. Pets get this through BasePet; wild and quest animals
pick it up by adding the mixin to their typeclass.

Two render paths per vocalisation, decided per listener:

    Listener has Condition.SPEAK_WITH_ANIMALS:
        sees  '{Animal.key} {action}  "{dialogue}"'
        — combined: vocalisation flavour PLUS the spoken meaning.

    Listener does NOT have the condition:
        sees  '{Animal.key} {action}'
        — pure third-person action. No "says" framing — that would tell the
          listener speech happened, breaking the no-tell principle that makes
          the speak_with_animals spell worth seeking out.

Lookup precedence:
    per-instance override (vocalisation_overrides / spoken_overrides)
        → species table in world/animals/vocalisations.py
            → species "_default" entry in the same table.

If neither side resolves a line for the (species, hook) pair, the call is a
no-op. That makes vocalize() safe to wire into command paths without forcing
table coverage for every conceivable hook.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.condition import Condition
from world.animals.vocalisations import get_spoken_line, get_vocalisation


class AnimalSpeakerMixin:
    """Adds vocalize() to any animal NPC."""

    species = AttributeProperty("")
    vocalisation_overrides = AttributeProperty(dict)
    spoken_overrides = AttributeProperty(dict)

    def _pick_action_line(self, hook):
        """Pick a non-speaker action line — instance override beats species table."""
        return self._pick_override(self.vocalisation_overrides, hook) or get_vocalisation(
            self.species, hook
        )

    def _pick_spoken_line(self, hook):
        """Pick a speaker dialogue line — instance override beats species table."""
        return self._pick_override(self.spoken_overrides, hook) or get_spoken_line(
            self.species, hook
        )

    @staticmethod
    def _pick_override(overrides, hook):
        """Resolve an override entry: pick from collection, return string as-is."""
        overrides = overrides or {}
        entry = overrides.get(hook)
        if not entry:
            return None
        if isinstance(entry, str):
            return entry
        # SaverList from AttributeProperty / regular list / tuple — all iterable.
        import random
        return random.choice(list(entry))

    def vocalize(self, hook):
        """Emit a hook-keyed vocalisation to the current room.

        Per-listener rendering — non-speakers see the action line, listeners
        with Condition.SPEAK_WITH_ANIMALS additionally see the dialogue line.
        """
        room = self.location
        if not room:
            return

        action = self._pick_action_line(hook)
        dialogue = self._pick_spoken_line(hook)

        if not action and not dialogue:
            return

        # Capitalise first letter of action ("sits down..." → "Sits down...")
        # without disturbing existing capitalisation later in the string.
        if action:
            action = action[:1].upper() + action[1:]

        for obj in room.contents:
            if obj is self:
                continue
            if not getattr(obj, "has_account", False):
                continue
            if hasattr(obj, "has_condition") and obj.has_condition(Condition.DEAF):
                # Deaf listeners still see the visible action; only the spoken
                # line is suppressed.
                if action:
                    obj.msg(f"{self.key} {action}")
                continue
            if getattr(obj, "position", None) == "sleeping":
                continue

            understands = (
                hasattr(obj, "has_condition")
                and obj.has_condition(Condition.SPEAK_WITH_ANIMALS)
            )

            if understands and dialogue:
                if action:
                    obj.msg(f'|c{self.key}|n {action}  |c"{dialogue}"|n')
                else:
                    obj.msg(f'|c{self.key}|n says in Animal:|n "{dialogue}"')
            elif action:
                obj.msg(f"|c{self.key}|n {action}")
