from evennia import DefaultScript
from evennia import ObjectDB
from django.conf import settings
from enums.hunger_level import HungerLevel

class HungerService(DefaultScript):
    """
    A global timer script that runs every 15 minutes and decrements each characters hunger level
    """

    def at_script_creation(self):
        # This makes the script persistent in the database
        self.key = "hunger_service"
        self.desc = "Runs every 15 minutes minute and decrements every characters hunger level"
        self.interval = settings.HUNGER_TICK_INTERVAL
        self.persistent = True
        self.start_delay = True  # wait interval before first run
        self.repeats = 0  # repeat forever

    def at_repeat(self):
        """
        This is called every `interval` seconds
        """
        for char in ObjectDB.objects.filter(db_typeclass_path__contains="Character"):

            # Superuser is exempt from hunger
            account = char.account
            if account and account.is_superuser:
                continue

            # Skip unpuppeted characters (quit but account still logged in)
            if not char.has_account:
                continue

            # Skip characters without hunger_level
            if not hasattr(char, "hunger_level"):
                continue

            hunger_level = char.hunger_level # This should be HungerLevel enum
            if not isinstance(hunger_level, HungerLevel):
                continue

            if hunger_level != HungerLevel.STARVING:
                if hunger_level == HungerLevel.FULL and char.hunger_free_pass_tick:
                    char.hunger_free_pass_tick = False
                else:
                    char.hunger_level = hunger_level.get_level(hunger_level.value - 1)