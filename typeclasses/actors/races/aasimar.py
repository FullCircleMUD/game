from enums.abilities_enum import Ability
from enums.size import Size
from typeclasses.actors.races.race_base import RaceBase

AASIMAR = RaceBase(
    key="aasimar",
    display_name="Aasimar",
    description=(
        "Aasimar are celestial-touched beings bearing a trace of divine heritage "
        "in their blood. Their otherworldly nature grants them resilience against "
        "the forces of darkness and a natural affinity for divine magic. They are "
        "often drawn to lives of purpose, serving as champions of the light."
    ),
    size=Size.MEDIUM,
    base_hp=12,
    base_mana=14,
    base_move=100,
    ability_score_bonuses={Ability.WIS: 1, Ability.CHA: 1},
    racial_effects=[
        {"type": "condition", "condition": "darkvision"},
        {"type": "damage_resistance", "damage_type": "necrotic", "value": 25},
    ],
    racial_languages=["celestial"],
    min_remort=2,
)
