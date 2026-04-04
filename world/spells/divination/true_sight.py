"""
True Sight — divination spell, available from SKILLED mastery.

Grants the caster progressively deeper magical perception as mastery
increases. Each tier unlocks a new layer of sight:

    SKILLED(2): See HIDDEN actors, objects, fixtures, and exits.
                Does NOT remove HIDDEN — caster silently sees through it.
    EXPERT(3):  + Auto-detect all traps (no perception roll needed).
    MASTER(4):  + See INVISIBLE entities (DETECT_INVIS condition).
    GM(5):      Duration only (60 min).

Duration scaling:
    SKILLED(2): 5 minutes,  mana 15
    EXPERT(3):  10 minutes, mana 25
    MASTER(4):  30 minutes, mana 40
    GM(5):      60 minutes, mana 40

Anti-stacking: can't recast while active (mana refunded).
Cooldown: 0 (duration-limited buff).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class TrueSight(Spell):
    key = "true_sight"
    aliases = ["ts"]
    name = "True Sight"
    school = skills.DIVINATION
    min_mastery = MasteryLevel.SKILLED
    mana_cost = {2: 15, 3: 25, 4: 40, 5: 40}
    target_type = "self"
    cooldown = 0
    description = "Grants magical sight that pierces concealment, traps, and invisibility."
    mechanics = (
        "Self-buff — tiered magical perception.\n"
        "SKILLED: see HIDDEN entities and objects.\n"
        "EXPERT: + auto-detect all traps (no roll needed).\n"
        "MASTER: + see INVISIBLE entities.\n"
        "Does NOT reveal them to others (only you can see them).\n"
        "Duration: 5min (Skilled), 10min (Expert), 30min (Master), 60min (GM).\n"
        "No cooldown — duration-limited."
    )

    # Duration in minutes per tier
    _DURATION_MINUTES = {2: 5, 3: 10, 4: 30, 5: 60}

    # Tier thresholds for capabilities
    _TRAP_TIER = 3      # EXPERT — auto-detect traps
    _INVIS_TIER = 4     # MASTER — see invisible

    def _execute(self, caster, target):
        # Anti-stacking — can't recast while active
        if caster.has_effect("true_sight"):
            tier = self.get_caster_tier(caster)
            caster.mana += self.mana_cost.get(tier, 0)
            return (False, {
                "first": "Your True Sight is already active.",
                "second": None,
                "third": None,
            })

        tier = self.get_caster_tier(caster)
        duration_minutes = self._DURATION_MINUTES.get(tier, 5)
        duration_seconds = duration_minutes * 60

        # Only MASTER+ gets DETECT_INVIS condition
        detect_invis = tier >= self._INVIS_TIER
        caster.apply_true_sight(duration_seconds, detect_invis=detect_invis)

        # Store tier so trap detection and other systems can check it
        caster.db.true_sight_tier = tier

        # EXPERT+ auto-detect traps in current room on cast
        if tier >= self._TRAP_TIER:
            self._detect_traps_in_room(caster)

        # Build tier-appropriate message
        min_s = "minute" if duration_minutes == 1 else "minutes"
        sight_desc = self._sight_description(tier)
        return (True, {
            "first": (
                f"|MYour eyes tingle with magical energy. "
                f"You can now see {sight_desc}! "
                f"({duration_minutes} {min_s})|n"
            ),
            "second": None,  # self-cast
            "third": (
                f"|M{caster.key}'s eyes begin to glow with a faint "
                f"magical light.|n"
            ),
        })

    def _sight_description(self, tier):
        """Return what this tier of True Sight reveals."""
        if tier >= self._INVIS_TIER:
            return "hidden things, traps, and the invisible"
        if tier >= self._TRAP_TIER:
            return "hidden things and traps"
        return "hidden things"

    def _detect_traps_in_room(self, caster):
        """Auto-detect all armed, undetected traps in caster's room."""
        room = caster.location
        if not room:
            return

        for obj in list(room.contents) + list(room.exits):
            if (
                hasattr(obj, "is_trapped")
                and obj.is_trapped
                and hasattr(obj, "trap_armed")
                and obj.trap_armed
                and hasattr(obj, "trap_detected")
                and not obj.trap_detected
            ):
                obj.detect_trap(caster)

        # Check room itself (pressure plates)
        if (
            hasattr(room, "is_trapped")
            and room.is_trapped
            and hasattr(room, "trap_armed")
            and room.trap_armed
            and hasattr(room, "trap_detected")
            and not room.trap_detected
        ):
            room.detect_trap(caster)
