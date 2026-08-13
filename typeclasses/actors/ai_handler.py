"""
AIHandler — persistent state machine for mob AI.

Borrowed from Evennia's EvAdventure contrib, adapted for FCM with
area-restricted movement and configurable target filtering.

Each tick, `run()` dispatches to `self.obj.ai_<state>()` on the mob.
State is persisted as an Evennia Attribute (survives server restarts).

Usage:
    class MyMob(StateMachineAIMixin, BaseNPC):
        def ai_wander(self):
            ...

    mob.ai.set_state("wander")
    mob.ai.run()  # called by ticker
"""

import random

from evennia.utils.logger import log_trace
from evennia.utils.utils import lazy_property


class AIHandler:
    """
    Persistent state machine for mob AI.

    Stores current state as an Evennia Attribute on the owning object.
    Each call to run() looks up ai_<state>() on the object and calls it.
    """

    attribute_name = "ai_state"
    attribute_category = "ai_state"

    def __init__(self, obj):
        self.obj = obj
        self._state = obj.attributes.get(
            self.attribute_name,
            category=self.attribute_category,
            default="idle",
        )

    def set_state(self, state):
        """Change AI state (persisted to DB)."""
        self._state = state
        self.obj.attributes.add(
            self.attribute_name, state,
            category=self.attribute_category,
        )

    def get_state(self):
        """Return current AI state string."""
        return self._state

    def run(self):
        """Dispatch to the mob's ai_<state>() method."""
        state = self.get_state()
        method = getattr(self.obj, f"ai_{state}", None)
        if method:
            try:
                method()
            except Exception:
                log_trace(f"AI error in {self.obj.key} (state: {state})")

    # ── Target helpers ──

    def get_targets_in_room(self, *predicates):
        """
        Return everything in the room this mob can perceive.

        Perception is the floor. ``p_can_see`` always applies and the
        supplied predicates narrow the result further — they can never
        widen it. A concealed actor is returned only when the mob holds
        the counter that reveals them: the ``true_sight`` effect for
        HIDDEN, the ``DETECT_INVIS`` condition for INVISIBLE.

        The mob decides what it *cares* about by passing predicates; it
        does not decide what it can *perceive*. Callers narrow with
        targeting-library predicates rather than filtering the returned
        list, so filtering stays uniform and debuggable across every
        call site::

            self.ai.get_targets_in_room(p_is_character)
            self.ai.get_targets_in_room(p_is_character, p_living,
                                        p_excluding(victim))

        Args:
            *predicates: ``(obj, caller) -> bool``, the targeting-library
                predicate shape. Prefer an existing library predicate;
                where none fits, add one rather than filtering inline.
                Accepts them loose or as a single list, so a mob can hold
                a named predicate stack as an attribute and pass it whole.
        """
        from utils.targeting.helpers import walk_contents
        from utils.targeting.predicates import p_can_see

        if len(predicates) == 1 and isinstance(predicates[0], (list, tuple)):
            predicates = tuple(predicates[0])

        mob = self.obj
        # Caller predicates lead: they are typically cheap isinstance
        # checks, so they short-circuit most candidates before p_can_see
        # does its method calls.
        return [
            obj
            for obj in walk_contents(mob, mob.location, *predicates, p_can_see)
            if obj is not mob
        ]

    # ── Movement helpers ──

    def get_area_exits(self):
        """
        Return the exits this mob can actually use, within its area.

        Two questions in sequence. Can the mob go that way at all —
        ``open_exits`` answers that, applying the traverse lock and height
        access, whether the mob can see the exit, and whether a door on it is
        open and unlocked. Then, should it: exits are narrowed to rooms
        sharing the mob's ``mob_area`` tag so populations stay in their zone.
        A mob with no area tag is unrestricted and gets the first answer.

        Every mob movement decision reaches this — ``wander``,
        ``flee_to_random_room``, ``_flee_from_threat``, ``_is_cornered`` and
        the wounded retreats — so a mob will not wander through a closed door,
        and a mob boxed in by one counts as cornered and turns to fight.

        Selection only. ``at_traverse`` on the chosen exit is what enforces
        passage, and applies gates these predicates cannot see (encumbrance,
        size, traps).
        """
        from utils.targeting.helpers import open_exits

        mob = self.obj
        if not mob.location:
            return []

        usable = open_exits(mob)

        area_tags = mob.tags.get(category="mob_area", return_list=True)
        area_tag = area_tags[0] if area_tags else None
        if not area_tag:
            return usable

        return [
            exi for exi in usable
            if area_tag in (
                exi.destination.tags.get(
                    category="mob_area", return_list=True
                ) or []
            )
        ]

    def pick_random_exit(self):
        """Pick a random exit within the mob's area. Returns exit or None."""
        exits = self.get_area_exits()
        return random.choice(exits) if exits else None


class StateMachineAIMixin:
    """Mixin that provides the .ai lazy property for any object."""

    @lazy_property
    def ai(self):
        return AIHandler(self)


# Backward-compat alias — remove after all imports are updated.
AIMixin = StateMachineAIMixin
