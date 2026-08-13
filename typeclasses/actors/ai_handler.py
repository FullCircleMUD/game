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

    def get_targets_in_room(self, target_filter=None):
        """
        Return potential targets the mob can currently perceive.

        Perception is the floor: ``target_filter`` narrows that set
        further, it never widens it. A concealed actor is returned only
        when the mob holds the counter that reveals them — ``true_sight``
        for HIDDEN, ``DETECT_INVIS`` for INVISIBLE.

        Args:
            target_filter: callable(obj) -> bool. If None, returns PCs.
        """
        from utils.targeting.predicates import p_can_see

        if not self.obj.location:
            return []
        if target_filter:
            return [
                obj for obj in self.obj.location.contents
                if obj != self.obj and target_filter(obj)
                and p_can_see(obj, self.obj)
            ]
        # Default: player characters only
        return [
            obj for obj in self.obj.location.contents
            if getattr(obj, "is_pc", False) and p_can_see(obj, self.obj)
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
