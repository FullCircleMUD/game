from enums.abilities_enum import Ability
from enums.size import Size
from enums.weapon_type import WeaponType
from typeclasses.actors.races.race_base import RaceBase

HALFLING = RaceBase(
    key="halfling",
    display_name="Halfling",
    description=(
        "Halflings are small, nimble folk with a natural talent for stealth "
        "and an uncanny knack for avoiding danger. What they lack in stature "
        "they make up for with quick reflexes and an irrepressible cheerfulness "
        "that makes them welcome companions on any adventure. Their small size "
        "and quiet nature grants them permanent advantage on stealth checks."
    ),
    size=Size.SMALL,
    base_hp=8,
    base_mana=10,
    base_move=80,
    ability_score_bonuses={Ability.DEX: 2, Ability.STR: -1},
    racial_languages=["halfling"],
    racial_weapon_proficiencies=[WeaponType.SLING],
    racial_skill_advantages=frozenset({"stealth"}),
)
