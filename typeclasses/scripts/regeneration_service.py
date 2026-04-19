from evennia import DefaultScript, SESSION_HANDLER
from evennia.utils import logger
from enums.hunger_level import HungerLevel
from enums.thirst_level import ThirstLevel
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
        self.desc = "Runs every 20 seconds and depending on characters hunger state regens, degens or does nothing to every character"
        self.interval = 20  # seconds
        self.persistent = True
        self.start_delay = True  # wait interval before first run
        self.repeats = 0  # repeat forever

    def at_repeat(self):
        """
        This is called every `interval` seconds (20s).
        Regen and pet healing run every tick. Degen only runs every 3rd tick
        so it stays on a 60s cadence — preserves the original death timelines
        without needing a second script.
        """
        # Tick counter lives on ndb — no need to persist across restarts.
        # Worst case after a reboot, one degen fires up to 40s late.
        self.ndb.tick_count = (self.ndb.tick_count or 0) + 1
        run_degen = self.ndb.tick_count % 3 == 0
        if run_degen:
            self.ndb.tick_count = 0

        for session in SESSION_HANDLER.get_sessions():
            try:
                self._process_character(session, run_degen)
            except Exception:
                char = session.get_puppet()
                logger.log_trace(f"Regen error for {char.key if char else 'unknown'}")

            # Regen active pets belonging to this character
            try:
                self._process_pets(session)
            except Exception:
                logger.log_trace("Pet regen error")

    def _process_character(self, session, run_degen):
        """Process regen/degen for a single character based on hunger AND thirst."""
        char = session.get_puppet()
        if not char:
            return

        # Skip characters without hunger_level
        if not hasattr(char, "hunger_level"):
            return

        hunger_level = char.hunger_level  # This should be HungerLevel enum
        if not isinstance(hunger_level, HungerLevel):
            return

        # Thirst is optional — characters that pre-date the thirst system
        # (or test fixtures that don't set it) get the legacy hunger-only path.
        thirst_level = getattr(char, "thirst_level", None)
        if not isinstance(thirst_level, ThirstLevel):
            thirst_level = None

        # Both meters must permit regen for healing to fire.
        # Either meter triggering degen is enough to bleed.
        hunger_allows_regen = hunger_level.value >= HungerLevel.PECKISH.value
        thirst_allows_regen = (
            thirst_level is None
            or thirst_level.value >= ThirstLevel.AWARE.value
        )

        hunger_is_degen = hunger_level.value <= HungerLevel.FAMISHED.value
        thirst_is_degen = (
            thirst_level is not None
            and thirst_level.value <= ThirstLevel.PARCHED.value
        )

        if hunger_allows_regen and thirst_allows_regen:
            self.regenerate(char)
        elif (hunger_is_degen or thirst_is_degen) and run_degen:
            self.degenerate(char, hunger_level, thirst_level)

        # Anything in between (HUNGRY, or DRY-through-VERY_THIRSTY) just blocks
        # regen without actively bleeding — no action needed here.

        self.send_hunger_messages(char, hunger_level)
        if thirst_level is not None:
            self.send_thirst_messages(char, thirst_level)


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

    def send_thirst_messages(self, character, thirst_level):
        # First-person nag once thirst drops below the no-penalty zone.
        if thirst_level.value <= ThirstLevel.AWARE.value:
            character.msg(thirst_level.get_thirst_message())

        # Room-visible third-person message once dehydration starts to show.
        if thirst_level.value <= ThirstLevel.PARCHED.value:
            if character.location:
                character.location.msg_contents(
                    thirst_level.get_thirst_message_third_person(character.key),
                    exclude=character,
                    from_obj=character,
                )

    def regenerate(self,character):

        # base rate = level / 4 rounded up + constitution bonus
        if hasattr(character, "total_level") and hasattr(character, "constitution"):
            con_bonus = character.get_attribute_bonus(character.constitution)
            if con_bonus < 0:
                con_bonus = 0

            base_rate = math.ceil(character.total_level / 4) + con_bonus
        else:
            base_rate = 1

        # Position multiplier: resting = 2x, sleeping = 3x, fighting = 0x
        multiplier = getattr(character, "REGEN_MULTIPLIERS", {}).get(
            getattr(character, "position", "standing"), 1
        )

        # Super-sleep rooms boost sleeping regen to 5x
        if (
            getattr(character, "position", "standing") == "sleeping"
            and character.location
            and getattr(character.location, "get_sleep_policy", lambda: None)() == "super"
        ):
            multiplier = 5

        if multiplier == 0:
            return  # no regen in combat

        # Spread the per-minute rate across three 20s ticks, floor of 1
        hp_regen = max(1, round(base_rate * multiplier / 3))
        mana_regen = max(1, round(base_rate * multiplier / 3))
        # movement regens faster than hits or mana because it gets used so quickly moving around
        move_regen = max(1, round(base_rate * multiplier * 2 / 3))

        character.hp = min(character.effective_hp_max, character.hp + hp_regen)
        character.mana = min(character.mana_max, character.mana + mana_regen)
        character.move = min(character.move_max, character.move + move_regen)

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

    def degenerate(self, character, hunger_level, thirst_level):
        """
        Bleed HP/MP/MV from a character whose hunger or thirst has tipped
        them into the degen zone. Runs once per minute (every 3rd 20s tick),
        so `cycles_to_death` reads as minutes.

        Each meter contributes a candidate (cycles_to_death, death_cause).
        We take the worst (smallest cycles_to_death) and use that rate +
        cause for the bleed. Hunger wins ties (it appears first) so
        "starved while also parched" is recorded as starvation.
        """
        candidates = []  # list of (cycles_to_death, death_cause)

        if hunger_level == HungerLevel.STARVING:
            candidates.append((15, "starvation"))
        elif hunger_level == HungerLevel.FAMISHED:
            candidates.append((30, "starvation"))

        if thirst_level == ThirstLevel.CRITICAL:
            candidates.append((15, "dehydration"))
        elif thirst_level == ThirstLevel.DEHYDRATED:
            candidates.append((25, "dehydration"))
        elif thirst_level == ThirstLevel.PARCHED:
            candidates.append((35, "dehydration"))

        if not candidates:
            return  # caller filtered for degen but neither meter qualified

        cycles_to_death, death_cause = min(candidates, key=lambda c: c[0])

        hp_loss = max(1, round(character.effective_hp_max / cycles_to_death))
        mana_loss = max(1, round(character.mana_max / cycles_to_death))
        move_loss = max(1, round(character.move_max / cycles_to_death))

        character.hp = max(0, character.hp - hp_loss)
        character.mana = max(0, character.mana - mana_loss)
        character.move = max(0, character.move - move_loss)

        if character.hp == 0:
            character.die(death_cause)