from enums.abilities_enum import Ability
from enums.size import Size
from typeclasses.actors.races.race_base import RaceBase

ELF = RaceBase(
    key="elf",
    display_name="Elf",
    description=(
        "Elves are a graceful and long-lived race, often dwelling in "
        "cities or wildlands. They are known for their sharp intellect, "
        "innate magical talent, and elegant appearance. Elves excel in "
        "both arts and combat, combining keen senses with refined skills."
    ),
    size=Size.MEDIUM,
    base_hp=8,
    base_mana=14,
    base_move=100,
    ability_score_bonuses={Ability.DEX: 1, Ability.INT: 1, Ability.CON: -1},
    racial_effects=[
        {"type": "condition", "condition": "darkvision"},
    ],
    racial_languages=["elfish"],
)
