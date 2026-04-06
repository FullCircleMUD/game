"""
Find Familiar — conjuration spell, available from BASIC mastery.

Summons a magical familiar that follows the caster. The core mechanic
is remote control — the caster sees through the familiar's eyes and
moves it room to room via pet commands.

Each mastery tier unlocks a more powerful familiar:
    BASIC(1):   Rat — small, goes anywhere                    mana 8
    SKILLED(2): Cat — stealth, doesn't trigger mob aggro       mana 12
    EXPERT(3):  Owl — can fly (aerial scouting)                mana 16
    MASTER(4):  Hawk — flies + fights alongside caster         mana 20
    GM(5):      Imp — flies + fights + illuminates dark rooms  mana 25

One familiar per caster (global). Recasting while one exists fails
with mana refund — dismiss or let the old one die first.

Remote control via pet commands:
    pet look          — see through familiar's eyes
    pet <direction>   — move familiar to adjacent room
    pet return        — teleport familiar back to caster
    pet dismiss       — destroy the familiar
"""

from evennia.utils.create import create_object

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# Familiar class path and display name per tier
_FAMILIAR_TIERS = {
    1: ("typeclasses.actors.pets.familiars.rat.FamiliarRat", "a rat"),
    2: ("typeclasses.actors.pets.familiars.cat.FamiliarCat", "a cat"),
    3: ("typeclasses.actors.pets.familiars.owl.FamiliarOwl", "an owl"),
    4: ("typeclasses.actors.pets.familiars.hawk.FamiliarHawk", "a hawk"),
    5: ("typeclasses.actors.pets.familiars.imp.FamiliarImp", "an imp"),
}


def _find_existing_familiar(caster_key):
    """Find any existing familiar created by this caster, anywhere in the game."""
    from evennia import ObjectDB
    # Search all objects for familiars with this creator_key
    candidates = ObjectDB.objects.filter(
        db_tags__db_key="familiar",
        db_tags__db_category="pet_type",
    )
    for obj in candidates:
        if getattr(obj, "is_familiar", False) and getattr(obj, "creator_key", None) == caster_key:
            return obj
    return None


@register_spell
class FindFamiliar(Spell):
    key = "find_familiar"
    aliases = ["familiar", "ff"]
    name = "Find Familiar"
    school = skills.CONJURATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 8, 2: 12, 3: 16, 4: 20, 5: 25}
    target_type = "none"
    cooldown = 0
    description = "Summons a magical familiar to serve as a companion and scout."
    mechanics = (
        "Summons a familiar that follows you and can be remote-controlled.\n"
        "Basic: rat. Skilled: cat (stealth). Expert: owl (flies).\n"
        "Master: hawk (flies + fights). GM: imp (flies + fights + light).\n"
        "One familiar per caster — dismiss or let it die before recasting.\n"
        "Use 'pet look', 'pet <direction>', 'pet return' to scout remotely.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)

        # Check for existing familiar (global — any owner)
        existing = _find_existing_familiar(caster.key)
        if existing:
            caster.mana += self.mana_cost.get(tier, 0)
            owner = getattr(existing, "owner_key", "unknown")
            if owner == caster.key:
                return (False,
                        "You already have a familiar. Use |wpet dismiss|n "
                        "to release it before summoning a new one.")
            else:
                return (False,
                        "A familiar you created still exists in the world. "
                        "Its current owner must dismiss it before you can "
                        "summon a new one.")

        # Determine familiar type
        typeclass_path, display_name = _FAMILIAR_TIERS.get(tier, _FAMILIAR_TIERS[1])

        # Create the familiar
        familiar = create_object(
            typeclass_path,
            key=display_name,
            location=caster.location,
            nohome=True,
        )

        # Set ownership and creator tracking
        familiar.creator_key = caster.key
        familiar.owner_key = caster.key
        familiar.tags.add("familiar", category="pet_type")

        # Start following
        familiar.start_following(caster)

        return (True, {
            "first": (
                f"|CYou complete the summoning ritual. {display_name.capitalize()} "
                f"materialises at your feet and looks up at you expectantly.|n\n"
                f"Use |wpet look|n, |wpet <direction>|n, |wpet return|n "
                f"to scout remotely."
            ),
            "second": None,
            "third": (
                f"|C{caster.key} completes a summoning ritual. "
                f"{display_name.capitalize()} materialises at their feet.|n"
            ),
        })
