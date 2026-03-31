"""
CellarRat — weak aggressive mob for the Harvest Moon cellar quest.

Small, fast, low HP. Attacks players on sight after a short delay.
Designed as dungeon instance mobs — no wander or respawn needed.

When the last mob in a room dies, the room's ``not_clear`` tag is
removed, unblocking forward exits for players to proceed.
"""

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.search import search_tag

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob


class CellarRat(AggressiveMob):
    """A large cellar rat. Aggressive but weak."""

    size = AttributeProperty("small")

    # ── Stats — level 1, fragile ──
    hp = AttributeProperty(2)
    hp_max = AttributeProperty(2)
    strength = AttributeProperty(4)
    dexterity = AttributeProperty(14)
    constitution = AttributeProperty(8)
    base_armor_class = AttributeProperty(10)
    armor_class = AttributeProperty(10)
    level = AttributeProperty(1)

    # ── Combat ──
    initiative_speed = AttributeProperty(3)
    damage_dice = AttributeProperty("1d2")
    attack_message = AttributeProperty("bites")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(4)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(1)

    # ── Display ──
    room_description = AttributeProperty(
        "{name} snarls from the shadows, teeth bared."
    )

    # ── Behavior ──
    ai_tick_interval = AttributeProperty(5)
    respawn_delay = AttributeProperty(0)  # dungeon mob, no respawn

    # ── AI States ──

    def ai_wander(self):
        """Seek players in room. No wandering (dungeon mob)."""
        if not self.location or not self.is_alive:
            return
        if self.scripts.get("combat_handler"):
            return
        players = self.ai.get_targets_in_room()
        if players:
            import random
            self._schedule_attack(random.choice(players))

    # ── Death — check room clearance ──

    def die(self, cause="unknown", killer=None):
        """On death, check if room is cleared and remove not_clear tag."""
        room = self.location
        super().die(cause, killer=killer)
        if room:
            _check_room_cleared(room)


def _check_room_cleared(room):
    """
    Check if all mobs in this dungeon room are dead.

    If so, remove the ``not_clear`` tag to unblock forward exits.
    This is a standalone function so other dungeon mob types can reuse it.
    """
    if not room.tags.has("not_clear", category="dungeon_room"):
        return  # already cleared

    # Check for living mobs in this specific room
    for obj in room.contents:
        if hasattr(obj, "is_alive") and obj.is_alive and hasattr(obj, "is_pc") and not obj.is_pc:
            return  # still mobs alive

    # All clear — remove the gate
    room.tags.remove("not_clear", category="dungeon_room")
    room.msg_contents("|gThe way forward is clear.|n")
