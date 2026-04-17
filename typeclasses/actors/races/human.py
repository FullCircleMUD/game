from enums.size import Size
from typeclasses.actors.races.race_base import RaceBase

HUMAN = RaceBase(
    key="human",
    display_name="Human",
    description=(
        "Humans are the most adaptable and ambitious of the common races. "
        "They have no particular strengths or weaknesses, making them suitable "
        "for any class or playstyle. Their balanced nature and determination "
        "make them excellent adventurers."
    ),
    size=Size.MEDIUM,
    base_hp=10,
    base_mana=10,
    base_move=100,
)
