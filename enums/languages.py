from enum import Enum


class Languages(Enum):
    # CHARACTER RACE LANGUAGES
    COMMON = "common"
    DWARVEN = "dwarven"
    ELFISH = "elfish"
    HALFLING = "halfling"
    CELESTIAL = "celestial"

    # OTHER LANGUAGES
    GOBLIN = "goblin"
    DRAGON = "dragon"

    # NO KOBOLD langauage, they speak dragon

    # NON-LEARNABLE — cannot be picked at chargen, not granted by races,
    # not unlocked by COMPREHEND_LANGUAGES. The only way to speak/understand
    # ANIMAL is via the SPEAK_WITH_ANIMALS condition (spell or potion).
    ANIMAL = "animal"
