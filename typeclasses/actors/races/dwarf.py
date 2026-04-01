from enums.abilities_enum import Ability
from enums.actor_size import ActorSize
from enums.weapon_type import WeaponType
from typeclasses.actors.races.race_base import RaceBase

DWARF = RaceBase(
    key="dwarf",
    display_name="Dwarf",
    description=(
        "Dwarves are a sturdy folk, renowned for their resilience and "
        "craftsmanship. Their hardy constitution and resistance to toxins "
        "make them excellent warriors. Though slower than other "
        "races, their durability more than compensates."
    ),
    size=ActorSize.MEDIUM,
    base_hp=14,
    base_mana=6,
    base_move=80,
    ability_score_bonuses={Ability.CON: 2, Ability.DEX: -1},
    racial_effects=[
        {"type": "condition", "condition": "darkvision"},
        {"type": "damage_resistance", "damage_type": "poison", "value": 30},
    ],
    racial_languages=["dwarven"],
    racial_weapon_proficiencies=[WeaponType.BATTLEAXE, WeaponType.HAMMER],
)
