"""
Tutorial 2 Builder — The Economic Loop.

Creates a per-player instance of Tutorial 2 with 6 rooms. All objects
are tagged with the instance key for cleanup.

Room layout:
    Hub → [1] Harvest Field → [2] Woodlot → [3] Windmill
    → [4] Bakery → [5] Vault → [6] Complete → Hub

Usage:
    Called by TutorialInstanceScript.start_tutorial(character, chunk_num=2).
    Returns the first room object.
"""

from evennia import create_object

from commands.room_specific_cmds.tutorial.cmdset_tutorial import CmdSetTutorial
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_harvesting import RoomHarvesting
from typeclasses.terrain.rooms.room_processing import RoomProcessing
from typeclasses.terrain.rooms.room_bank import RoomBank
from utils.exit_helpers import connect_bidirectional_exit


def build_tutorial_2(instance):
    """
    Build all Tutorial 2 rooms, exits, and items.

    Args:
        instance: TutorialInstanceScript managing this tutorial.

    Returns:
        The first room (Harvest Field).
    """
    tag = instance.instance_key
    rooms = {}

    # ================================================================== #
    #  Helpers
    # ================================================================== #

    def _room(key, desc, tutorial_text, guide_context=None,
              typeclass=RoomBase, **extra_attrs):
        attrs = [("desc", desc), ("tutorial_text", tutorial_text)]
        if guide_context:
            attrs.append(("guide_context", guide_context))
        attrs.extend(extra_attrs.get("attributes", []))

        room = create_object(typeclass, key=key, attributes=attrs)
        room.tags.add(tag, category="tutorial_room")
        room.cmdset.add(CmdSetTutorial, persistent=True)
        room.always_lit = True
        room.allow_combat = False
        room.allow_pvp = False
        room.allow_death = False
        return room

    def _connect_bidirectional_exit(room_a, room_b, direction, **kwargs):
        """Create tagged bidirectional exits."""
        exit_ab, exit_ba = connect_bidirectional_exit(room_a, room_b, direction, **kwargs)
        exit_ab.tags.add(tag, category="tutorial_exit")
        exit_ba.tags.add(tag, category="tutorial_exit")
        return exit_ab, exit_ba

    def _spawn_pip(room):
        """Spawn a tutorial guide NPC in this room."""
        guide_context = getattr(room.db, "guide_context", "") or ""
        tutorial_text = getattr(room.db, "tutorial_text", "") or ""
        pip = create_object(
            "typeclasses.actors.npcs.tutorial_guide_npc.TutorialGuideNPC",
            key="Pip",
            location=room,
        )
        pip.tags.add(tag, category="tutorial_mob")
        pip.llm_personality = (
            "A bright-eyed young adventurer who works at the Harvest Moon "
            "Inn. Rowan the bartender sent you to show new arrivals the "
            "ropes. You're enthusiastic, helpful, and speak plainly."
        )
        pip.llm_knowledge = (
            "You are guiding a player through Tutorial 2: The Economic Loop. "
            f"You are currently in {room.key}.\n\n"
            f"WHAT TO TEACH IN THIS ROOM:\n{guide_context}\n\n"
            f"INSTRUCTIONS YOU ALREADY SHOWED THE PLAYER:\n{tutorial_text}"
        )
        pip.room_description = (
            "{name}, a bright-eyed young guide, is here ready to help."
        )
        return pip

    # Check first-run status
    char = instance.get_character()
    first_run = (
        char and char.account
        and not getattr(char.account.db, "tutorial_2_entered", False)
    )

    if first_run and char.account:
        char.account.db.tutorial_2_entered = True
        # Give starter gold for processing costs (restored by snapshot on exit)
        char.receive_gold_from_reserve(20)

    # ================================================================== #
    #  ROOM 1: Harvest Field — Harvesting wheat
    # ================================================================== #

    rooms["harvest"] = _room(
        "The Harvest Field",
        "Golden stalks of wheat sway gently in the breeze across a "
        "sun-drenched field. A well-worn path leads east toward a "
        "cluster of workshops.",
        "|wTutorial: Harvesting|n\n\n"
        "  |wharvest|n — Gather resources from the land.\n"
        "  |winventory|n (|wi|n) — Check what you've gathered.\n\n"
        "Different areas yield different resources. This field has wheat.\n\n"
        "|yPractice:|n\n"
        "  Type |wharvest|n a few times to gather wheat.\n"
        "  Check |winventory|n to see your wheat count.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach the player to |wharvest|n wheat. Each harvest gathers "
            "resources that go into their inventory. They can check with "
            "|winventory|n. Suggest harvesting a few times before moving on."
        ),
        typeclass=RoomHarvesting,
    )
    rooms["harvest"].resource_id = 1  # Wheat
    rooms["harvest"].harvest_command = "harvest"
    rooms["harvest"].resource_count = 50 if first_run else 0
    rooms["harvest"].abundance_threshold = 5
    rooms["harvest"].desc_abundant = (
        "The wheat field stretches out, thick with ripe golden stalks."
    )
    rooms["harvest"].desc_scarce = (
        "Only a few stalks of wheat remain standing in the field."
    )
    rooms["harvest"].desc_depleted = (
        "The field has been harvested clean. Nothing remains to gather."
    )
    _spawn_pip(rooms["harvest"])

    # ================================================================== #
    #  ROOM 2: Woodlot — Chopping wood
    # ================================================================== #

    rooms["woodlot"] = _room(
        "The Woodlot",
        "A small stand of timber surrounds a clearing littered with "
        "wood chips and sawdust. An axe mark scarred stump serves as "
        "a chopping block. The path continues east.",
        "|wTutorial: Chopping|n\n\n"
        "  |wchop|n — Chop wood from trees.\n\n"
        "Different resources use different harvest commands:\n"
        "  |wharvest|n — crops, |wchop|n — wood, |wmine|n — ore,\n"
        "  |wpick|n — cotton, |wgather|n — herbs & rare materials.\n\n"
        "|yPractice:|n\n"
        "  Type |wchop|n a few times to gather wood.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach |wchop|n for gathering wood. Explain that different "
            "resources use different harvest commands: |wharvest|n for "
            "crops, |wchop|n for wood, |wmine|n for ore, |wpick|n for "
            "cotton, |wgather|n for herbs and rare materials."
        ),
        typeclass=RoomHarvesting,
    )
    rooms["woodlot"].resource_id = 6  # Wood
    rooms["woodlot"].harvest_command = "chop"
    rooms["woodlot"].resource_count = 50 if first_run else 0
    rooms["woodlot"].abundance_threshold = 5
    rooms["woodlot"].desc_abundant = (
        "Plenty of timber stands ready for the axe."
    )
    rooms["woodlot"].desc_scarce = (
        "Only a few thin trees remain in the woodlot."
    )
    rooms["woodlot"].desc_depleted = (
        "The woodlot has been cleared. No trees remain."
    )
    _connect_bidirectional_exit(rooms["harvest"], rooms["woodlot"], "east")
    _spawn_pip(rooms["woodlot"])

    # ================================================================== #
    #  ROOM 3: Windmill — Processing wheat to flour
    # ================================================================== #

    rooms["windmill"] = _room(
        "The Windmill",
        "A wooden windmill creaks and groans as its great sails turn "
        "in the wind. Inside, heavy millstones grind grain into fine "
        "flour. A chute deposits finished flour into sacks below.",
        "|wTutorial: Processing|n\n\n"
        "  |wprocess|n — Convert raw resources into refined goods.\n"
        "  |wrates|n — See what this station can process and the cost.\n\n"
        "Processing costs gold. Here, 1 wheat becomes 1 flour for 1 gold.\n\n"
        "|yPractice:|n\n"
        "  Type |wrates|n to see the conversion.\n"
        "  Type |wprocess|n to mill some wheat into flour.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach |wprocess|n and |wrates|n. This windmill converts "
            "1 wheat into 1 flour for 1 gold. |wrates|n shows what the "
            "station can do. Processing costs gold — raw resources become "
            "refined goods. Suggest they process some wheat."
        ),
        typeclass=RoomProcessing,
    )
    rooms["windmill"].processing_type = "windmill"
    rooms["windmill"].recipes = [
        {"inputs": {1: 1}, "output": 2, "amount": 1, "cost": 1},
    ]
    _connect_bidirectional_exit(rooms["woodlot"], rooms["windmill"], "east")
    _spawn_pip(rooms["windmill"])

    # ================================================================== #
    #  ROOM 4: Bakery — Processing flour+wood to bread
    # ================================================================== #

    rooms["bakery"] = _room(
        "The Bakery",
        "A brick oven dominates this cozy workshop, radiating heat. "
        "Sacks of flour lean against the wall, and split logs are "
        "stacked beside the oven for fuel. The smell of baking bread "
        "is mouthwatering.",
        "|wTutorial: Multi-Input Processing|n\n\n"
        "  Some recipes need multiple inputs.\n"
        "  Here: 1 flour + 1 wood → 1 bread (1 gold).\n\n"
        "This is the full chain:\n"
        "  |wharvest|n wheat → |wprocess|n flour → |wprocess|n bread\n\n"
        "Bread is food — use |weat bread|n when hungry.\n\n"
        "|yPractice:|n\n"
        "  Check |wrates|n, then |wprocess|n some bread.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach multi-input processing. This bakery turns 1 flour + "
            "1 wood into 1 bread for 1 gold. Explain the full chain: "
            "harvest wheat → mill flour → bake bread. Bread is food — "
            "|weat bread|n when hungry. Suggest checking |wrates|n first."
        ),
        typeclass=RoomProcessing,
    )
    rooms["bakery"].processing_type = "bakery"
    rooms["bakery"].recipes = [
        {"inputs": {2: 1, 6: 1}, "output": 3, "amount": 1, "cost": 1},
    ]
    _connect_bidirectional_exit(rooms["windmill"], rooms["bakery"], "east")
    _spawn_pip(rooms["bakery"])

    # ================================================================== #
    #  ROOM 5: Vault — Banking
    # ================================================================== #

    rooms["vault"] = _room(
        "The Vault",
        "A heavy iron door opens into a stone vault lined with locked "
        "strongboxes. A clerk sits behind a reinforced counter, ready "
        "to manage deposits and withdrawals.",
        "|wTutorial: Banking|n\n\n"
        "  |wbalance|n — Check your bank holdings.\n"
        "  |wdeposit <amount> <resource>|n — Store resources in the bank.\n"
        "  |wwithdraw <amount> <resource>|n — Take resources from the bank.\n\n"
        "Your bank account is shared across ALL your characters on "
        "this account. Resources stored in the bank are safe — they "
        "can't be lost on death.\n\n"
        "|yPractice:|n\n"
        "  Check your |wbalance|n.\n"
        "  Try |wdeposit 1 bread|n to store some bread.\n"
        "  Try |wwithdraw 1 bread|n to take it back.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach banking. |wbalance|n shows holdings. "
            "|wdeposit <amount> <resource>|n stores resources safely. "
            "|wwithdraw <amount> <resource>|n retrieves them. The bank "
            "is account-level — shared across all characters. Resources "
            "in the bank can't be lost on death."
        ),
        typeclass=RoomBank,
    )
    _connect_bidirectional_exit(rooms["bakery"], rooms["vault"], "east")
    _spawn_pip(rooms["vault"])

    # ================================================================== #
    #  ROOM 6: Tutorial Complete
    # ================================================================== #

    rooms["complete"] = _room(
        "Tutorial Complete",
        "A bright archway glows at the end of this final chamber. "
        "Inscribed on the wall is a summary of the economic skills "
        "you've learned.",
        "|wTutorial 2 Complete!|n\n\n"
        "You've learned the economic loop:\n\n"
        "  |wHarvesting:|n   harvest, chop, mine, forage, fish, hunt\n"
        "  |wProcessing:|n   process, rates\n"
        "  |wBanking:|n      balance, deposit, withdraw\n\n"
        "The full chain: harvest → process → consume or bank.\n"
        "Head to Tutorial 3 to learn about character growth!\n\n"
        "|yMove |weast|y to return to the Tutorial Hub and "
        "receive your graduation reward!|n",
        guide_context=(
            "Congratulate the player! They've learned the economic loop: "
            "harvesting, processing, and banking. Recap the full chain: "
            "harvest → process → consume or bank. Mention Tutorial 3 "
            "covers character growth and social features. Tell them "
            "|weast|n takes them to the hub for their reward."
        ),
    )
    _connect_bidirectional_exit(rooms["vault"], rooms["complete"], "east")
    _spawn_pip(rooms["complete"])

    # ================================================================== #
    #  Completion exit back to hub
    # ================================================================== #

    hub = instance.hub_room
    if hub:
        from world.tutorial.tutorial_exit import TutorialCompletionExit

        exit_to_hub = create_object(
            TutorialCompletionExit,
            key="Tutorial Hub",
            location=rooms["complete"],
            destination=hub,
            attributes=[
                ("tutorial_instance_id", instance.id),
            ],
        )
        exit_to_hub.set_direction("east")
        exit_to_hub.tags.add(tag, category="tutorial_exit")

    return rooms["harvest"]
