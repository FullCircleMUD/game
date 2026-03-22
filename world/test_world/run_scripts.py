
from evennia import create_script
from evennia import search_script
from evennia import GLOBAL_SCRIPTS

#from typeclasses.scripts.regeneration_service import RegenerationService



def run_scripts():


        # Check if hunger timer exists
    existing = GLOBAL_SCRIPTS.regeneration_service
    if not existing:
        create_script(
            "typeclasses.scripts.regeneration_service.RegenerationService",
            key="regeneration_service",
            obj=None
        )
        print("Regeneration service started.")
    else:
        print("Regeneration service already running.")

    
            # Check if hunger timer exists
    existing = GLOBAL_SCRIPTS.hunger_service
    if not existing:
        create_script(
            "typeclasses.scripts.hunger_service.HungerService",
            key="hunger_service",
            obj=None
        )
        print("Hunger service started.")
    else:
        print("Hunger service already running.")