from enum import Enum

# USED IN THE HUNGER SUB SYSTEM
class HungerLevel(Enum):
    FULL = 8         # WHEN CHARACTER EATS TO FULL
    # - SOMEHOW GIVE THEM A DOUBLE BANGER SO THEY DON'T DROP TO SATISFIED A SECOND LATER
    #   IF THEY HAVE BAD LUCK WITH TIMING THE CYCLE PROCESSING
    #   OTHER WISE DROP ONE LEVEL PER HUNGER CYCLE
    SATISFIED = 7    # WHEN CHARACTER EATS TO SATISFIED
    NOURISHED = 6    # NO PENALTY — wider runway before the damage zone
    CONTENT = 5      # NO PENALTY — wider runway before the damage zone
    PECKISH = 4      # WHEN CHARACTER EATS TO PECKISH (last no-penalty stage)
    HUNGRY = 3       # CHARACTER NO LONGER REGENERATES
    FAMISHED = 2     # CHARACTER LOSES HEALTH, MANA & MOVEMENT SPEED 30 REGEN CYCLES TO DEATH CALCULATION
    STARVING = 1     # CHARACTER LOSES HEALTH, MANA & MOVEMENT SPEED 10 REGEN CYCLES TO DEATH CALCULATION
    # DEAD IS NOT A HUNGER LEVEL, IT IS A CONDITION THAT IS HANDLED BY THE REGENERATION SYSTEM
    # WHICH PROGESSIVELY TAKES HP, MANA AND MOVEMENT SPEED OFF CHARACTERS WHO ARE STARVING UNTIL THEY DIE AT 0 HP
    # CONCEIVABLY THEY COULD BURN A LOT HEALING POTIONS OR SPELLS TO KEEP THEM ALIVE UNTIL THEY CAN GET SOME FOOD


    # NOTING THAT A REGEN CYCLE IS CURRENTLY 1 MINUTE LONG
    # AND A HUNGER CYCLE IS ANTICIAPTED TO BE 15 OR 20 MINUTES LONG
    # SO 30 REGEN CYCLES IS 30 MINUTES 
    #       - SO STARTING AT FULL HEALTH THEY WOULD LOSE 50% - 66% OF THEIR HEALTH 
    #           BEFORE DROPPING TO NEXT HUNGER LEVEL (STARVING)
    # SO 10 REGEN CYCLES IS 10 MINUTES
    #       - SO STARTING AT FULL HEALTH A STARVING CHARACTER WOULD STARVE TO DEATH IN 10 MINUTES

    
    def get_hunger_message(self) -> str:
        """Get appropriate first-person message for this hunger level"""
        return _HUNGER_MESSAGES.get(self, "Your hunger level is unknown.")
    
    def get_hunger_message_third_person(self, character_key: str) -> str:
        """Get appropriate third-person message for this hunger level (what others observe)"""
        template = _HUNGER_MESSAGES_THIRD_PERSON.get(self, f"{character_key} looks about the same as usual.")
        return template.format(name=character_key)


    def get_level(self, num):
        """Get the HungerLevel by its value"""
        return _HUNGER_REVERSE_LOOKUP[num]

    def get_name(self, num):
        """Get the text name of the hunger level"""
        return _HUNGER_NAME_LOOKUP[num]


# Define first-person messages after the enum class
_HUNGER_MESSAGES = {
    HungerLevel.FULL: "You feel completely satisfied and full of energy!",
    HungerLevel.SATISFIED: "You feel well-fed and content.",
    HungerLevel.NOURISHED: "You feel comfortably nourished.",
    HungerLevel.CONTENT: "Your appetite is settled — no thoughts of food just now.",
    HungerLevel.PECKISH: "You're starting to feel a bit peckish.",
    HungerLevel.HUNGRY: "Your stomach is growling - you're getting quite hungry.",
    HungerLevel.FAMISHED: "You're famished! Your hunger is affecting your strength.",
    HungerLevel.STARVING: "You're starving! You feel weak and desperate for food."
}

# Define third-person messages (what others observe)
_HUNGER_MESSAGES_THIRD_PERSON = {
    HungerLevel.FULL: "{name} looks satisfied and energetic, with a contented expression.",
    HungerLevel.SATISFIED: "{name} appears well-fed and comfortable.",
    HungerLevel.NOURISHED: "{name} looks comfortably fed.",
    HungerLevel.CONTENT: "{name} looks fine — no sign of hunger.",
    HungerLevel.PECKISH: "{name} occasionally glances around, perhaps looking for food.",
    HungerLevel.HUNGRY: "{name}'s stomach makes audible growling sounds.",
    HungerLevel.FAMISHED: "{name} looks noticeably weaker and keeps clutching their stomach.",
    HungerLevel.STARVING: "{name} appears gaunt and desperate, clearly in need of food."
}

# HUNGER LEVEL REVERSE LOOKUP
# This allows us to find the hunger level
_HUNGER_REVERSE_LOOKUP = {
    1: HungerLevel.STARVING,
    2: HungerLevel.FAMISHED,
    3: HungerLevel.HUNGRY,
    4: HungerLevel.PECKISH,
    5: HungerLevel.CONTENT,
    6: HungerLevel.NOURISHED,
    7: HungerLevel.SATISFIED,
    8: HungerLevel.FULL,
}


# MASTERY LEVEL REVERSE LOOKUP
# This allows us to find the MasteryLevel enum member by its name (string)
_HUNGER_NAME_LOOKUP = {
    1: "STARVING",
    2: "FAMISHED",
    3: "HUNGRY",
    4: "PECKISH",
    5: "CONTENT",
    6: "NOURISHED",
    7: "SATISFIED",
    8: "FULL",
}


