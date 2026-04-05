"""
Detect Traps — divination spell, available from BASIC mastery.

Grants heightened awareness of traps in the caster's vicinity.
Automatically reveals traps in the current room and provides
passive trap detection as the caster moves.

Scaling (duration and sensitivity):
    BASIC(1):   5 min,  mana 4  — reveals traps in current room
    SKILLED(2): 10 min, mana 6  — + passive detection on room entry
    EXPERT(3):  15 min, mana 8  — + bonus to disarm attempts
    MASTER(4):  30 min, mana 10 — + reveals hidden doors
    GM(5):      1 hour, mana 14 ��� + reveals traps in adjacent rooms

Recasting refreshes duration.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class DetectTraps(Spell):
    key = "detect_traps"
    aliases = ["dtrap", "dt"]
    name = "Detect Traps"
    school = skills.DIVINATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 14}
    target_type = "self"
    cooldown = 0
    description = "Magically heightens awareness of traps and hidden dangers."
    mechanics = (
        "Reveals all traps in the current room on cast.\n"
        "Skilled+: passive trap detection when entering rooms.\n"
        "Expert+: bonus to disarm attempts.\n"
        "Master+: also reveals hidden doors.\n"
        "GM: detects traps in adjacent rooms.\n"
        "Duration: 5 min (Basic) to 1 hour (GM).\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Detect Traps implementation pending — needs immediate trap "
            "reveal in current room (call detect_trap on all TrapMixin "
            "objects), timed buff for passive detection on move, "
            "disarm bonus at EXPERT+, hidden door reveal at MASTER+."
        )
