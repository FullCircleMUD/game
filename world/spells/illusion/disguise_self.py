"""
Disguise Self — illusion spell, available from BASIC mastery.

Changes the caster's appearance to look like a different person.
Other players and NPCs see the disguised name and description.

Scaling:
    BASIC(1):   Change name only, 10 min,         mana 4
    SKILLED(2): Change name + desc, 30 min,        mana 6
    EXPERT(3):  Change name + desc + race, 1 hour, mana 8
    MASTER(4):  + bypass NPC faction hostility, 2 hours, mana 10
    GM(5):      + undetectable by True Sight, 4 hours,   mana 14

Breaks on entering combat. Detect Magic or True Sight reveals the
disguise (except at GM). Uses spell_arg for the disguise name.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class DisguiseSelf(Spell):
    key = "disguise_self"
    aliases = ["disguise", "dis"]
    name = "Disguise Self"
    school = skills.ILLUSION
    min_mastery = MasteryLevel.BASIC
    has_spell_arg = True
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 14}
    target_type = "self"
    cooldown = 0
    description = "Magically alters your appearance to look like someone else."
    mechanics = (
        "Changes caster's visible name (and desc/race at higher tiers).\n"
        "Basic: name only / 10 min. Skilled: + desc / 30 min.\n"
        "Expert: + race / 1 hour. Master: + bypass faction hostility / 2 hours.\n"
        "GM: undetectable by True Sight / 4 hours.\n"
        "Breaks on entering combat. Detect Magic reveals the disguise.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Disguise Self implementation pending — needs spell_arg for "
            "disguise name, temporary name/desc override on caster, "
            "combat-break hook, True Sight/Detect Magic reveal check, "
            "NPC faction bypass at MASTER+."
        )
