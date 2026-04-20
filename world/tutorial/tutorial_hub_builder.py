"""
Tutorial Hub — static room built once by the world builder.

The hub is the gateway between tutorials. It is NOT instanced — it's
a permanent world room. Players return here between tutorial chunks
and can re-enter tutorials or leave for the game world.

Exits:
    east  — Tutorial 1: Survival Basics
    north — Tutorial 2: The Economic Loop
    west  — Tutorial 3: Growth & Social
    south — Exit to the game world

Usage:
    from world.tutorial.tutorial_hub_builder import build_tutorial_hub
    hub = build_tutorial_hub()
"""

from evennia import create_object, ObjectDB
from evennia.utils.search import search_tag

from typeclasses.terrain.rooms.room_base import RoomBase


TUTORIAL_HUB_TAG = "tutorial_hub"


def get_tutorial_hub():
    """Return the existing tutorial hub room, or None."""
    results = search_tag(TUTORIAL_HUB_TAG, category="tutorial_hub")
    results = list(results)
    if results:
        return results[0]
    return None


def build_tutorial_hub():
    """
    Build the Tutorial Hub room. Idempotent — returns existing hub if found.

    Returns:
        The tutorial hub room object.
    """
    existing = get_tutorial_hub()
    if existing:
        return existing

    hub = create_object(
        RoomBase,
        key="Tutorial Hub",
        attributes=[
            ("desc",
             "You stand in a warm, well-lit chamber with smooth stone walls. "
             "Glowing runes line the doorways, each leading to a different lesson. "
             "A calm voice seems to echo from the walls themselves:\n\n"
             "|c\"Welcome, traveller. These halls will teach you the ways of "
             "this world. Each doorway leads to a different set of lessons. "
             "You may take them in order, or leave for the world "
             "beyond at any time.\"|n\n\n"
             "  |weast|n  - |cTutorial 1: Survival Basics|n\n"
             "           Movement, looking, inventory, equipment, combat, and more.\n"
             "  |wnorth|n - |cTutorial 2: The Economic Loop|n\n"
             "           Harvesting, processing, and banking.\n"
             "  |wwest|n  - |cTutorial 3: Growth & Social|n\n"
             "           Skills, training, guilds, and groups.\n"
             "  |wsouth|n - Leave the tutorial for the game world.\n\n"
             "You can always return here later with |wtutorial|n."),
            ("max_height", 0),
            ("max_depth", 0),
            ("natural_light", True),
            ("tutorial_text",
             "|wWelcome to the Tutorial Hub!|n\n\n"
             "This is your starting point for learning the game. Each direction "
             "leads to a different tutorial:\n\n"
             "  |weast|n  - |cTutorial 1: Survival Basics|n\n"
             "           Movement, looking, inventory, equipment, flying,\n"
             "           swimming, light, combat, eating, and help.\n\n"
             "  |wnorth|n - |cTutorial 2: The Economic Loop|n\n"
             "           Harvesting, processing, and banking.\n\n"
             "  |wwest|n  - |cTutorial 3: Growth & Social|n\n"
             "           Character info, communication, skills,\n"
             "           training, guilds, and groups.\n\n"
             "  |wsouth|n - Leave the tutorial\n\n"
             "You can always return with |wtutorial|n."),
        ],
    )

    # Tag so we can find it
    hub.tags.add(TUTORIAL_HUB_TAG, category="tutorial_hub")

    # Zone/district tags (for the `where` command)
    hub.tags.add("tutorial", category="zone")
    hub.tags.add("tutorial_hub", category="district")

    # Add the tutorial CmdSet (for `tutorial` room command)
    from commands.room_specific_cmds.tutorial.cmdset_tutorial import CmdSetTutorial
    hub.cmdset.add(CmdSetTutorial, persistent=True)

    # Tutorial rooms are always lit
    hub.always_lit = True

    # Safe zone
    hub.allow_combat = False
    hub.allow_pvp = False
    hub.allow_death = False

    # ── Create exits ──────────────────────────────────────────────
    from typeclasses.terrain.exits.exit_tutorial_hub import (
        ExitTutorialStart, ExitTutorialReturn,
    )

    # East — Tutorial 1: Survival Basics
    exit_e = create_object(
        ExitTutorialStart,
        key="Tutorial 1: Survival Basics",
        location=hub,
        destination=hub,  # destination unused — at_traverse handles it
    )
    exit_e.set_direction("east")
    exit_e.db.tutorial_num = 1
    exit_e.db.desc = "Movement, looking, inventory, equipment, combat, and more."

    # North — Tutorial 2: The Economic Loop
    exit_n = create_object(
        ExitTutorialStart,
        key="Tutorial 2: The Economic Loop",
        location=hub,
        destination=hub,
    )
    exit_n.set_direction("north")
    exit_n.db.tutorial_num = 2
    exit_n.db.desc = "Harvesting, processing, and banking."

    # West — Tutorial 3: Growth & Social
    exit_w = create_object(
        ExitTutorialStart,
        key="Tutorial 3: Growth & Social",
        location=hub,
        destination=hub,
    )
    exit_w.set_direction("west")
    exit_w.db.tutorial_num = 3
    exit_w.db.desc = "Skills, training, guilds, and groups."

    # South — Exit to game world
    exit_s = create_object(
        ExitTutorialReturn,
        key="Exit to the game world",
        location=hub,
        destination=hub,  # destination unused — at_traverse handles it
    )
    exit_s.set_direction("south")
    exit_s.db.desc = "Leave the tutorial for the game world."

    return hub
