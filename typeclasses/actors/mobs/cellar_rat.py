"""
CellarRat — weak aggressive mob for the Harvest Moon cellar quest.

Small, fast, low HP. Attacks players on sight after a short delay.
Designed as dungeon instance mobs — no wander or respawn needed.

When the last mob in a room dies, the room's ``not_clear`` tag is
removed, unblocking forward exits for players to proceed.
"""

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.search import search_tag

from enums.damage_type import DamageType
from enums.size import Size
from typeclasses.actors.mob import CombatMob
from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from utils.targeting.predicates import (
    p_is_character,
    p_is_typeclass,
    p_living,
)


class CellarRat(AggressiveMob):
    """A large cellar rat. Aggressive but weak."""

    base_size = AttributeProperty(Size.TINY.value)
    size = AttributeProperty(Size.TINY.value)

    # ── Stats — level 1, fragile ──
    hp = AttributeProperty(2)
    base_hp_max = AttributeProperty(2)
    hp_max = AttributeProperty(2)
    base_strength = AttributeProperty(4)
    strength = AttributeProperty(4)
    base_dexterity = AttributeProperty(14)
    dexterity = AttributeProperty(14)
    base_constitution = AttributeProperty(8)
    constitution = AttributeProperty(8)
    base_armor_class = AttributeProperty(10)
    armor_class = AttributeProperty(10)
    level = AttributeProperty(1)

    # ── Combat ──
    initiative_speed = AttributeProperty(3)
    damage_dice = AttributeProperty("1d2")
    damage_type = AttributeProperty(DamageType.PIERCING)
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

    # ── AI States ──

    def ai_wander(self):
        """Seek players in room. No wandering (dungeon mob)."""
        if not self.location or not self.is_alive:
            return
        if self.scripts.get("combat_handler"):
            return

        players = self.ai.get_targets_in_room(p_is_character)
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

    # Check for living mobs in this specific room.
    #
    # "A living combat mob" is the whole test. Players and pets both
    # fall out of the typeclass half: BasePet derives from BaseNPC, not
    # CombatMob, so a player's pet standing in the room does not hold
    # the exits shut.
    #
    # No caller: this is a state question about the room, not a
    # perception question, so there is no observer to pass.
    for obj in room.contents:
        if p_living(obj, None) and p_is_typeclass(CombatMob)(obj, None):
            return  # still mobs alive

    # All clear — remove the gate
    room.tags.remove("not_clear", category="dungeon_room")
    room.msg_contents("|gThe way forward is clear.|n")
