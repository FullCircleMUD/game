"""
AIHandler — persistent state machine for mob AI.

Borrowed from Evennia's EvAdventure contrib, adapted for FCM with
area-restricted movement and configurable target filtering.

Each tick, `run()` dispatches to `self.obj.ai_<state>()` on the mob.
State is persisted as an Evennia Attribute (survives server restarts).

Usage:
    class MyMob(AIMixin, BaseNPC):
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
        Return potential targets in the mob's current room.

        Args:
            target_filter: callable(obj) -> bool. If None, returns PCs.
        """
        if not self.obj.location:
            return []
        if target_filter:
            return [
                obj for obj in self.obj.location.contents
                if obj != self.obj and target_filter(obj)
            ]
        # Default: player characters only
        return [
            obj for obj in self.obj.location.contents
            if getattr(obj, "is_pc", False)
        ]

    # ── Movement helpers ──

    def get_area_exits(self):
        """
        Return exits leading to rooms tagged with the mob's area_tag.

        Uses the 'mob_area' tag category. If the mob has no area_tag,
        returns all traversable exits (no restriction).
        """
        mob = self.obj
        area_tag = getattr(mob, "area_tag", None)
        if not mob.location:
            return []

        all_exits = [
            exi for exi in mob.location.exits
            if exi.access(mob, "traverse") and exi.destination
        ]

        if not area_tag:
            return all_exits

        return [
            exi for exi in all_exits
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


class AIMixin:
    """Mixin that provides the .ai lazy property for any object."""

    @lazy_property
    def ai(self):
        return AIHandler(self)
