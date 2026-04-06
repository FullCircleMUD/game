from evennia import DefaultScript, SESSION_HANDLER
from evennia.utils import logger
from enums.hunger_level import HungerLevel
import math

class RegenerationService(DefaultScript):
    """
    A global timer script that runs every minute
    and depending on characters hunger state
    regens, degens or does nothing
    """

    def at_script_creation(self):
        # This makes the script persistent in the database
        self.key = "regeneration_service"
        self.desc = "Runs every minute and depending on characters hunger state regens, degens or does nothing to every character"
        self.interval = 60  # seconds
        self.persistent = True
        self.start_delay = True  # wait interval before first run
        self.repeats = 0  # repeat forever

    def at_repeat(self):
        """
        This is called every `interval` seconds
        """
        for session in SESSION_HANDLER.get_sessions():
            try:
                self._process_character(session)
            except Exception:
                char = session.get_puppet()
                logger.log_trace(f"Regen error for {char.key if char else 'unknown'}")

            # Regen active pets belonging to this character
            try:
                self._process_pets(session)
            except Exception:
                logger.log_trace("Pet regen error")

    def _process_character(self, session):
        """Process regen/degen for a single character."""
        char = session.get_puppet()
        if not char:
            return

        # Skip characters without hunger_level
        if not hasattr(char, "hunger_level"):
            return

        hunger_level = char.hunger_level # This should be HungerLevel enum
        if not isinstance(hunger_level, HungerLevel):
            return

        if hunger_level.value >= HungerLevel.PECKISH.value:
            # FULL, SATISFIED, PECKISH regenerate
            self.regenerate(char)
            return
        elif hunger_level.value <= HungerLevel.FAMISHED.value:
            # FAMISHED or STARVING - degen
            self.degenerate(char)

        # HungerLevel.HUNGRY not covered because no action take on this, no regen OR degen

        self.send_hunger_messages(char, hunger_level)


    def _process_pets(self, session):
        """Regen HP for active pets belonging to this session's character."""
        char = session.get_puppet()
        if not char or not char.location:
            return

        for obj in char.location.contents:
            if not getattr(obj, "is_pet", False):
                continue
            if getattr(obj, "owner_key", None) != char.key:
                continue
            if getattr(obj, "pet_state", None) == "stabled":
                continue

            # Check pet hunger — starving pets don't regen, dead pets die
            hunger = obj.check_hunger() if hasattr(obj, "check_hunger") else "fed"
            if hunger == "dead":
                obj.die(cause="starvation")
                continue
            if hunger == "starving":
                continue  # no regen while starving

            # Simple HP regen: 1 per tick (pets are simpler than characters)
            hp_max = getattr(obj, "hp_max", 0)
            if hp_max > 0 and obj.hp < hp_max:
                obj.hp = min(hp_max, obj.hp + 1)

    def send_hunger_messages(self, character, hunger_level):
        
        if hunger_level.value <= HungerLevel.PECKISH.value:
            # Print message to character (first-person)
            character.msg(hunger_level.get_hunger_message())

            
        if hunger_level.value <= HungerLevel.FAMISHED.value:
            # Print message to room (third-person) (only when they are getting very hungry)
            if character.location:
                character.location.msg_contents(
                    hunger_level.get_hunger_message_third_person(character.key),
                    exclude=character,
                    from_obj=character,
                )

    def regenerate(self,character):

        # regen rate = level / 4 rounded up + constitution bonus
        if hasattr(character, "total_level") and hasattr(character, "constitution"):
            con_bonus = character.get_attribute_bonus(character.constitution)
            if con_bonus < 0:
                con_bonus = 0

            regen_rate = math.ceil(character.total_level / 4) + con_bonus
        else:
            regen_rate = 1

        # Position multiplier: resting = 2x, sleeping = 3x
        multiplier = getattr(character, "REGEN_MULTIPLIERS", {}).get(
            getattr(character, "position", "standing"), 1
        )
        regen_rate *= multiplier

        character.hp = min(character.effective_hp_max, character.hp + regen_rate)
        character.mana = min(character.mana_max, character.mana + regen_rate)
        # regen movement saster than hits or mana because it gets used so quickly moving around
        character.move = min(character.move_max, character.move + (regen_rate * 2))

        # old regen amoutn logic from pre evennia FCM
        # based on taking 20 turns to regen to full health
        """
        health_per_tick = max(1, round(character.max_hp / config.sub_system_regeneration.regen_cycles_to_full_health))
        character.health = min(character.max_health, character.health + health_per_tick)

        mana_per_tick = max(1, round(character.max_mana / config.sub_system_regeneration.regen_cycles_to_full_mana))
        character.mana = min(character.max_mana, character.mana + mana_per_tick)

        movement_per_tick = max(1, round(character.max_movement / config.sub_system_regeneration.regen_cycles_to_full_move))
        character.movement = min(character.max_movement, character.movement + movement_per_tick)    
        """

    def degenerate(self, character):

        if character.hunger_level == HungerLevel.FAMISHED:
            cycles_to_death = 30
        else:
            #HungerLevel.STARVING
            cycles_to_death = 15

        hp_loss = max(1, round(character.effective_hp_max / cycles_to_death))
        mana_loss = max(1, round(character.mana_max / cycles_to_death))
        move_loss = max(1, round(character.move_max / cycles_to_death))

        character.hp = max(0, character.hp - hp_loss)
        character.mana = max(0, character.mana - mana_loss)
        character.move = max(0, character.move - move_loss)

        if character.hp == 0:
            character.die("starvation")