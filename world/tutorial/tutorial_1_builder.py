"""
Tutorial 1 Builder — Survival Basics.

Creates a per-player instance of Tutorial 1 with 10 rooms. All objects
are tagged with the instance key for cleanup.

Room layout:
    Hub → [1] Welcome → [2] Look → [3] Inventory → [4] Armoury
    → [5] Courtyard (fly/swim within room) → [6] Dark Passage
    → [7] Combat Arena → [8] Pantry → [9] Wellspring
    → [10] Complete → Hub

Usage:
    Called by TutorialInstanceScript.start_tutorial(character, chunk_num=1).
    Returns the first room object.
"""

from evennia import create_object

from commands.room_specific_cmds.tutorial.cmdset_tutorial import CmdSetTutorial
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware
from typeclasses.world_objects.fountain_fixture import FountainFixture
from utils.exit_helpers import connect_bidirectional_exit


def _spawn_nft_item(item_type_name, location, instance_tag):
    """
    Spawn a real NFT-backed item and tag it for tutorial cleanup.

    Uses the standard NFT lifecycle: assign_to_blank_token → spawn_into.
    The item gets all prototype attributes (damage, wearslot, etc.) from
    the registered prototype. On tutorial collapse, item.delete() returns
    the token to RESERVE via at_object_delete → NFTService.despawn.
    """
    from typeclasses.items.base_nft_item import BaseNFTItem

    token_id = BaseNFTItem.assign_to_blank_token(item_type_name)
    obj = BaseNFTItem.spawn_into(token_id, location)
    obj.db.tutorial_item = True
    obj.tags.add(instance_tag, category="tutorial_item")
    return obj


def build_tutorial_1(instance):
    """
    Build all Tutorial 1 rooms, exits, items and mobs.

    Args:
        instance: TutorialInstanceScript managing this tutorial.

    Returns:
        The first room (Welcome Hall).
    """
    tag = instance.instance_key
    rooms = {}

    # ================================================================== #
    #  Helper: create a tagged room with tutorial CmdSet
    # ================================================================== #

    def _room(key, desc, tutorial_text, guide_context=None, **extra_attrs):
        attrs = [("desc", desc), ("tutorial_text", tutorial_text)]
        if guide_context:
            attrs.append(("guide_context", guide_context))
        attrs.extend(extra_attrs.get("attributes", []))

        room = create_object(RoomBase, key=key, attributes=attrs)
        room.tags.add(tag, category="tutorial_room")
        room.cmdset.add(CmdSetTutorial, persistent=True)
        room.always_lit = True
        room.allow_combat = extra_attrs.get("allow_combat", False)
        room.allow_pvp = False
        room.allow_death = extra_attrs.get("allow_death", False)
        if "natural_light" in extra_attrs:
            room.db.natural_light = extra_attrs["natural_light"]
        if "sheltered" in extra_attrs:
            room.db.sheltered = extra_attrs["sheltered"]
        if "max_height" in extra_attrs:
            room.db.max_height = extra_attrs["max_height"]
        if "max_depth" in extra_attrs:
            room.db.max_depth = extra_attrs["max_depth"]
        if "vert_descriptions" in extra_attrs:
            room.vert_descriptions = extra_attrs["vert_descriptions"]
        return room

    def _connect_bidirectional_exit(room_a, room_b, direction, **kwargs):
        """Create tagged bidirectional exits."""
        exit_ab, exit_ba = connect_bidirectional_exit(room_a, room_b, direction, **kwargs)
        exit_ab.tags.add(tag, category="tutorial_exit")
        exit_ba.tags.add(tag, category="tutorial_exit")
        return exit_ab, exit_ba

    def _item(typeclass, key, location, desc, **extra_attrs):
        """Create a tagged tutorial item."""
        attrs = [("desc", desc), ("tutorial_item", True)]
        attrs.extend(extra_attrs.get("attributes", []))
        obj = create_object(typeclass, key=key, location=location, attributes=attrs)
        obj.tags.add(tag, category="tutorial_item")
        return obj

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
            "You are guiding a player through Tutorial 1: Survival Basics. "
            f"You are currently in {room.key}.\n\n"
            f"WHAT TO TEACH IN THIS ROOM:\n{guide_context}\n\n"
            f"INSTRUCTIONS YOU ALREADY SHOWED THE PLAYER:\n{tutorial_text}"
        )
        pip.room_description = (
            "{name}, a bright-eyed young guide, is here ready to help."
        )
        return pip

    # ================================================================== #
    #  ROOM 1: Welcome Hall — Movement
    # ================================================================== #

    rooms["welcome"] = _room(
        "Welcome Hall",
        "You stand in a spacious stone hall with high arched ceilings. "
        "Torches line the walls, casting warm light across the flagstone "
        "floor. A shimmering portal behind you leads back to the hub, "
        "and a passage opens to the east.",
        "|wTutorial: Movement|n\n\n"
        "In this world, you move by typing compass directions:\n"
        "  |wnorth|n (|wn|n), |wsouth|n (|ws|n), "
        "|weast|n (|we|n), |wwest|n (|ww|n)\n"
        "  |wup|n (|wu|n), |wdown|n (|wd|n)\n\n"
        "You can also move diagonally: |wnortheast|n (|wne|n), etc.\n\n"
        "Exits are listed when you |wlook|n (|wl|n) at a room. Try it now!\n\n"
        "|yPractice:|n Move |weast|n to continue to the next room.",
        guide_context=(
            "Welcome the player to the tutorial. Explain they move by "
            "typing compass directions like |weast|n, |wnorth|n, etc. "
            "Mention |wlook|n shows exits. Suggest they type |weast|n "
            "to continue."
        ),
    )

    _spawn_pip(rooms["welcome"])

    # ================================================================== #
    #  ROOM 2: Observation Chamber — Looking at Things
    # ================================================================== #

    rooms["look"] = _room(
        "Observation Chamber",
        "A quiet chamber lined with curiosities. An ornate sword rests "
        "on a display rack against one wall, and a weathered sign hangs "
        "beside the doorway. Everything here seems placed for you to study.",
        "|wTutorial: Looking at Things|n\n\n"
        "  |wlook|n (|wl|n) — See the room description, exits, and contents.\n"
        "  |wlook <thing>|n — Look at a specific object or person.\n\n"
        "|yPractice:|n\n"
        "  Try |wlook sword|n to inspect the display sword.\n"
        "  Try |wlook sign|n to read the sign.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach the player to examine things. |wlook|n shows the room. "
            "|wlook <thing>|n examines objects. Point out the sword and "
            "sign and suggest they try |wlook sword|n and |wlook sign|n. "
            "Also mention |wlook self|n and |wlook <player>|n."
        ),
    )
    _connect_bidirectional_exit(rooms["welcome"], rooms["look"], "east")

    _spawn_pip(rooms["look"])

    # Display sword (fixture — can't be picked up)
    from typeclasses.world_objects.base_fixture import WorldFixture

    sword_fixture = create_object(
        WorldFixture,
        key="an ornate display sword",
        location=rooms["look"],
        attributes=[
            ("desc",
             "A beautifully crafted longsword mounted on a wooden rack. "
             "The blade gleams in the torchlight, etched with flowing "
             "script in an ancient language. A small plaque reads: "
             "'For display only — do not touch.'"),
            ("tutorial_item", True),
        ],
    )
    sword_fixture.tags.add(tag, category="tutorial_item")
    sword_fixture.aliases.add("sword")
    sword_fixture.aliases.add("display sword")

    sign_fixture = create_object(
        WorldFixture,
        key="a weathered sign",
        location=rooms["look"],
        attributes=[
            ("desc",
             "|c--- Adventurer's Tip ---|n\n\n"
             "Use |wlook|n (|wl|n) to observe your surroundings.\n"
             "Use |wlook <thing>|n to inspect specific objects or people.\n\n"
             "The world is full of things to discover. Look carefully!"),
            ("tutorial_item", True),
        ],
    )
    sign_fixture.tags.add(tag, category="tutorial_item")
    sign_fixture.aliases.add("sign")

    # Room details for objects mentioned in the description
    rooms["look"].details = {
        "plaque": "A small brass plaque reads: 'For display only — do not touch.'",
        "torches": "Iron sconces hold flickering torches that cast dancing shadows.",
    }

    # ================================================================== #
    #  ROOM 3: Supply Room — Inventory (get/drop)
    # ================================================================== #

    rooms["inventory"] = _room(
        "Supply Room",
        "Wooden shelves line this small storeroom, most of them empty. "
        "A few items have been left out on a table for you to take: a "
        "backpack and a wooden shield. Some gold glitters on the floor.",
        "|wTutorial: Inventory & Items|n\n\n"
        "  |wget <item>|n — Pick up an item from the room.\n"
        "  |wget all|n — Pick up everything in the room.\n"
        "  |wdrop <item>|n — Drop an item from your inventory.\n"
        "  |winventory|n (|wi|n) — See what you're carrying.\n"
        "  |wget gold|n — Pick up gold coins.\n"
        "  |wget <amount> gold|n — Pick up a specific amount of gold.\n"
        "  |wget all gold|n — Pick up all gold in the room.\n"
        "  |wweight|n — Check how much you're carrying vs your limit.\n\n"
        "Backpacks are containers — you can store items inside them:\n"
        "  |wput <item> in backpack|n — Store an item in a container.\n"
        "  |wget <item> from backpack|n — Retrieve a stored item.\n\n"
        "|yPractice:|n\n"
        "  Pick up the backpack, shield, and gold.\n"
        "  Try |wput shield in backpack|n.\n"
        "  Check your |winventory|n.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach picking up items. |wget <item>|n picks things up, "
            "|wdrop <item>|n drops them, |winventory|n (or |wi|n) shows "
            "what you're carrying. Suggest they grab the backpack, shield, "
            "and gold. Mention backpacks are containers — |wput shield "
            "in backpack|n. Also mention |wweight|n to check carrying "
            "capacity."
        ),
    )
    _connect_bidirectional_exit(rooms["look"], rooms["inventory"], "east")

    rooms["inventory"].details = {
        "shelves": "Wooden shelves line the walls, mostly bare. A few items sit on a table.",
        "table": "A sturdy wooden table with a few items laid out for you to take.",
    }

    _spawn_pip(rooms["inventory"])

    # Backpack (real NFT container item)
    _spawn_nft_item("Backpack", rooms["inventory"], tag)

    # Wooden Shield (real NFT holdable item)
    _spawn_nft_item("Wooden Shield", rooms["inventory"], tag)

    # Check if this is the player's first tutorial run
    char = instance.get_character()
    first_run = (
        char and char.account
        and not getattr(char.account.db, "tutorial_1_entered", False)
    )

    # Gold on the floor (first run only — prevents gold farming)
    if first_run:
        rooms["inventory"].receive_gold_from_reserve(5)

    # ================================================================== #
    #  ROOM 4: Armoury — Equipment (wear/wield/remove)
    # ================================================================== #

    rooms["armoury"] = _room(
        "The Armoury",
        "Weapon racks and armour stands fill this room. On a velvet "
        "cushion sits a gleaming ring, and a strange cloth mask hangs "
        "nearby. A sturdy quarterstaff leans against the wall, and a "
        "leather cap hangs from a peg.",
        "|wTutorial: Equipment|n\n\n"
        "  |wwear <item>|n — Put on armour, rings, or clothing.\n"
        "  |wwield <item>|n — Ready a weapon for combat.\n"
        "  |whold <item>|n — Hold an item (torches, shields).\n"
        "  |wremove <item>|n — Unequip a worn/wielded item.\n"
        "  |wequipment|n (|weq|n) — See what you have equipped.\n\n"
        "|yPractice:|n\n"
        "  |wwield staff|n to ready the quarterstaff.\n"
        "  |wwear cap|n to put on the leather cap.\n"
        "  |wwear skydancer|n and |wwear n95|n.\n"
        "  Check your |wequipment|n.\n\n"
        "|yIMPORTANT:|n The ring grants FLY and the mask grants "
        "WATER_BREATHING — you'll need both in the next room!",
        guide_context=(
            "Teach equipping items. |wwear <item>|n puts on armour or "
            "accessories. |wwield <item>|n readies weapons. |whold <item>|n "
            "for shields and torches. |wremove <item>|n unequips. "
            "|wequipment|n (or |weq|n) shows gear. Tell them to wield the "
            "staff, wear the cap, and IMPORTANTLY wear the ring and mask — "
            "the ring grants FLY and the mask grants WATER_BREATHING, "
            "they'll need both in the next room."
        ),
    )
    _connect_bidirectional_exit(rooms["inventory"], rooms["armoury"], "east")

    _spawn_pip(rooms["armoury"])

    # Skydancer's Ring (real NFT item — grants FLY condition)
    _spawn_nft_item("Skydancer's Ring", rooms["armoury"], tag)

    # Aquatic N95 (real NFT item — grants WATER_BREATHING condition)
    _spawn_nft_item("Aquatic N95", rooms["armoury"], tag)

    # Quarterstaff (real NFT item — usable by almost all classes)
    _spawn_nft_item("Quarterstaff", rooms["armoury"], tag)

    # Leather cap (real NFT item)
    _spawn_nft_item("Leather Cap", rooms["armoury"], tag)

    # ================================================================== #
    #  ROOM 5: Open Courtyard — Flying & Swimming hub
    # ================================================================== #

    rooms["courtyard"] = _room(
        "Open Courtyard",
        "A wide courtyard open to the sky above. Puffy clouds drift "
        "overhead, and a gentle breeze rustles through the space. In "
        "the center, a crystal-clear pool shimmers invitingly, its "
        "depths glowing with a faint blue light. The passage continues "
        "east into a dark tunnel.",
        "|wTutorial: Flying & Swimming|n\n\n"
        "Some rooms allow vertical movement. You stay in the same room —\n"
        "the description changes to show what you see from your new height.\n\n"
        "  |wfly up|n / |wfly down|n — Move through the air (requires "
        "the FLY condition).\n"
        "  |wswim down|n / |wswim up|n — Dive underwater or surface.\n\n"
        "The |wSkydancer's Ring|n grants the FLY condition. Without it,\n"
        "you can't |wfly up|n — and if you lose the condition while\n"
        "airborne, you'll |rfall and take damage|n!\n\n"
        "The |wAquatic N95|n lets you breathe underwater. Without water\n"
        "breathing, you have limited breath based on your Constitution\n"
        "and take |rdrowning damage|n when it runs out!\n\n"
        "|yPractice:|n\n"
        "  Make sure you're wearing the ring and mask (check |weq|n).\n"
        "  Try |wfly up|n to soar above the courtyard.\n"
        "  Then |wfly down|n to return to the ground.\n"
        "  Try |wswim down|n to dive into the pool.\n"
        "  Then |wswim up|n to surface.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Explain flying and swimming. |wfly up|n and |wfly down|n "
            "for air movement — needs the FLY condition from the ring. "
            "|wswim down|n and |wswim up|n for water — the mask grants "
            "WATER_BREATHING. Without these conditions, flying fails and "
            "swimming drains breath. Make sure they check |weq|n for the "
            "ring and mask before trying."
        ),
        max_height=1,
        max_depth=-1,
        natural_light=True,
        vert_descriptions={
            0: (
                "A wide courtyard open to the sky above. Puffy clouds drift "
                "overhead, and a gentle breeze rustles through the space. In "
                "the center, a crystal-clear pool shimmers invitingly, its "
                "depths glowing with a faint blue light. The passage "
                "continues east into a dark tunnel."
            ),
            1: (
                "The wind rushes past you as you hover above the courtyard. "
                "Below, the crystal-clear pool is a disc of brilliant blue, "
                "its glow visible even from up here. The courtyard walls "
                "stretch out in every direction, and you can see the dark "
                "mouth of the eastern tunnel from a whole new angle. Puffy "
                "clouds drift close enough to touch."
            ),
            -1: (
                "You are submerged in the pool. A soft blue glow emanates "
                "from the smooth stones lining the bottom, casting rippling "
                "light across your hands. The sounds of the courtyard above "
                "are muffled and distant. Shafts of sunlight pierce the "
                "surface, dancing through the crystal-clear water."
            ),
        },
    )
    _connect_bidirectional_exit(rooms["armoury"], rooms["courtyard"], "east")
    _spawn_pip(rooms["courtyard"])
    # Barriers hide ground-level NPCs from flyers and swimmers
    rooms["courtyard"].visibility_up_barrier = (1, "medium")
    rooms["courtyard"].visibility_down_barrier = (-1, "medium")

    # ================================================================== #
    #  ROOM 6: The Dim Passage — Light & Darkness
    # ================================================================== #

    rooms["dark"] = _room(
        "The Dim Passage",
        "A narrow stone passage stretches before you. Without a light "
        "source, the darkness here would be absolute. Dampness seeps "
        "from the walls, and your footsteps echo in the confined space. "
        "An unlit torch rests in a wall sconce, and a tinderbox sits "
        "on a small ledge.",
        "|wTutorial: Light & Darkness|n\n\n"
        "Some rooms have no natural light. In the dark, you can't see:\n"
        "  - The room description\n"
        "  - Exits\n"
        "  - Items and characters\n\n"
        "To see in the dark:\n"
        "  |wlight <item>|n — Light a torch or lantern you're holding.\n"
        "  |wextinguish <item>|n — Put out your light source.\n"
        "  Some races have |wDARKVISION|n and can see without light.\n\n"
        "Light sources burn fuel over time. You can check remaining fuel "
        "by looking at the item.\n\n"
        "|yPractice:|n\n"
        "  If you're wielding a two-handed weapon, |wremove|n it first.\n"
        "  Pick up the torch: |wget torch|n\n"
        "  Hold it: |whold torch|n\n"
        "  Light it: |wlight torch|n\n"
        "  Now you can see! Move |weast|n when ready.",
        guide_context=(
            "This room is dark! Explain that some rooms have no natural "
            "light. They need to |wget torch|n, |whold torch|n, then "
            "|wlight torch|n to see. Mention some races have DARKVISION. "
            "If they're wielding a two-handed weapon, they need to "
            "|wremove|n it first to hold the torch."
        ),
        natural_light=False,
        sheltered=True,
    )
    _connect_bidirectional_exit(rooms["courtyard"], rooms["dark"], "east")

    _spawn_pip(rooms["dark"])

    # Wooden torch (real NFT item)
    _spawn_nft_item("Wooden Torch", rooms["dark"], tag)

    # ================================================================== #
    #  ROOM 7: Training Arena — Combat
    # ================================================================== #

    rooms["combat"] = _room(
        "Training Arena",
        "A circular arena with sand-covered floors and padded walls. "
        "Wooden weapon racks line the perimeter, and a straw-stuffed "
        "training dummy stands in the center, swaying slightly. Scratch "
        "marks and dents cover its surface from countless practice sessions.",
        "|wTutorial: Combat|n\n\n"
        "  |wattack <target>|n (|wkill|n) — Start fighting a target.\n"
        "  |wdodge|n — Sacrifice your next attack to make enemies less "
        "likely to hit you.\n"
        "  |wflee|n — Attempt to escape combat.\n"
        "  |wscore|n — View your character summary.\n\n"
        "Combat is automatic once started — you and your target take "
        "turns attacking based on weapon speed. The training dummy hits "
        "back lightly, so watch your HP!\n\n"
        "This room has |gno death penalty|n, so don't worry about dying.\n\n"
        "|yPractice:|n\n"
        "  |wattack dummy|n to start combat.\n"
        "  Try |wdodge|n during combat.\n"
        "  Check your |wstats|n to see your HP.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Time for combat! |wattack dummy|n (or |wkill dummy|n) starts "
            "a fight. Combat is automatic — they take turns attacking. "
            "Teach |wdodge|n to sacrifice an attack for defense, and "
            "|wflee|n to escape. Mention |wscore|n and |wstats|n to "
            "check HP. This room has no death penalty, so no risk."
        ),
        allow_combat=True,
        allow_death=False,
        natural_light=True,
    )
    _connect_bidirectional_exit(rooms["dark"], rooms["combat"], "east")

    _spawn_pip(rooms["combat"])

    # Training Dummy
    from typeclasses.actors.mobs.training_dummy import TrainingDummy

    dummy = create_object(
        TrainingDummy,
        key="a training dummy",
        location=rooms["combat"],
        attributes=[
            ("desc",
             "A straw-stuffed mannequin lashed to a wooden post with "
             "fraying rope. Its burlap skin is covered in slash marks "
             "and dents from countless practice sessions. Two button "
             "eyes stare blankly ahead, and a crudely painted smile "
             "stretches across its sackcloth face."),
        ],
    )
    dummy.tags.add(tag, category="tutorial_mob")
    dummy.aliases.add("dummy")
    dummy.aliases.add("training dummy")
    # Set spawn room so it respawns here
    dummy.spawn_room_id = rooms["combat"].id
    dummy.start_ai()

    # ================================================================== #
    #  ROOM 8: The Pantry — Eating & Hunger
    # ================================================================== #

    rooms["pantry"] = _room(
        "The Pantry",
        "A cozy pantry lined with wooden shelves. The smell of freshly "
        "baked bread fills the air. Several loaves sit on a stone "
        "counter, alongside a jug of water.",
        "|wTutorial: Eating & Hunger|n\n\n"
        "Your character gets hungry over time. Hunger levels:\n"
        "  |gFULL|n → SATED → PECKISH → |yHUNGRY|n → |rSTARVING|n\n\n"
        "When STARVING, you take periodic damage! Keep fed.\n\n"
        "  |weat bread|n — Eat bread to restore hunger.\n"
        "  |whunger|n — Check your current hunger level.\n"
        "  |wscore|n — Also shows hunger level.\n\n"
        "Bread is made from flour + wood (fuel) at a bakery.\n"
        "Flour is milled from wheat at a windmill.\n"
        "Wheat is harvested from farmland.\n\n"
        "You'll learn about harvesting, processing, and crafting "
        "in Tutorial 2!\n\n"
        "|yPractice:|n\n"
        "  Pick up bread from the room: |wget bread|n\n"
        "  Eat it: |weat bread|n\n"
        "  Check your hunger: |whunger|n\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Explain hunger. Characters get hungry over time: FULL → "
            "SATED → PECKISH → HUNGRY → STARVING. Starving causes "
            "damage! |weat bread|n restores hunger. |whunger|n checks "
            "level. Suggest picking up bread and eating it. Mention "
            "bread comes from wheat→flour→bread chain — Tutorial 2 "
            "covers the economics."
        ),
    )
    _connect_bidirectional_exit(rooms["combat"], rooms["pantry"], "east")

    _spawn_pip(rooms["pantry"])

    # Place bread only for first-time players (prevents tutorial bread farming)
    if first_run:
        char.account.db.tutorial_1_entered = True
        rooms["pantry"].receive_resource_from_reserve(3, 3)
    else:
        rooms["pantry"].db.desc += (
            "\n\n|xThe bread shelves are empty — bread is only provided "
            "on your first run through the tutorial.|n"
        )

    # ================================================================== #
    #  ROOM 9: The Wellspring — Drinking & Thirst
    # ================================================================== #

    rooms["wellspring"] = _room(
        "The Wellspring",
        "A cool stone chamber where a natural spring feeds a stone "
        "fountain set into the wall. The sound of running water echoes "
        "softly. An empty leather canteen sits on a ledge beside the "
        "fountain.",
        "|wTutorial: Drinking & Thirst|n\n\n"
        "Like hunger, your character gets thirsty over time.\n"
        "Thirst levels:\n"
        "  |gREFRESHED|n → HYDRATED → ... → |yDRY|n → THIRSTY "
        "→ ... → |rCRITICAL|n\n\n"
        "When DRY, health regeneration halts.\n"
        "When CRITICAL, you take damage and will die!\n\n"
        "  |wget canteen|n — Pick up the canteen.\n"
        "  |wrefill canteen fountain|n — Fill it at a fountain (5 drinks).\n"
        "  |wdrink canteen|n — Take a drink (restores one thirst stage).\n"
        "  |wscore|n — Shows your current thirst level.\n\n"
        "Canteens are refillable at any fountain in the world. "
        "Keep one in your inventory and refill whenever you find water.\n\n"
        "|yPractice:|n\n"
        "  Pick up the canteen: |wget canteen|n\n"
        "  Fill it: |wrefill canteen fountain|n\n"
        "  Take a drink: |wdrink canteen|n\n"
        "  Check your thirst: |wscore|n\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach the thirst system. Characters get thirsty over time, "
            "parallel to hunger. REFRESHED is full, DRY halts regen, "
            "CRITICAL causes death. |wget canteen|n picks up the canteen, "
            "|wrefill canteen fountain|n fills it at the fountain (5 drinks), "
            "|wdrink canteen|n takes a drink restoring one thirst stage. "
            "|wscore|n shows thirst level. Canteens are refillable at "
            "any fountain. Suggest they pick up the canteen, fill it, "
            "drink, and check score."
        ),
    )
    _connect_bidirectional_exit(rooms["pantry"], rooms["wellspring"], "east")

    _spawn_pip(rooms["wellspring"])

    # Fountain for refilling
    fountain = create_object(
        FountainFixture,
        key="a stone fountain",
        location=rooms["wellspring"],
        attributes=[
            ("desc",
             "A stone fountain fed by a natural spring. Clear, cold water "
             "flows steadily. You can refill a water container here with "
             "|wrefill canteen fountain|n."),
        ],
    )
    fountain.db.tutorial_item = True
    fountain.tags.add(tag, category="tutorial_item")
    fountain.aliases.add("fountain")

    # Empty canteen for practice
    _spawn_nft_item("Canteen", rooms["wellspring"], tag)

    # ================================================================== #
    #  ROOM 10: Tutorial Complete — Help & Exit
    # ================================================================== #

    rooms["complete"] = _room(
        "Tutorial Complete",
        "A bright archway glows at the end of this final chamber. "
        "Inscribed on the wall is a summary of everything you've learned, "
        "and beyond the arch lies the Tutorial Hub.",
        "|wTutorial 1 Complete!|n\n\n"
        "You've learned the survival basics:\n\n"
        "  |wMovement:|n     n/s/e/w/u/d, fly up/down, swim up/down\n"
        "  |wLooking:|n      look, look <thing>, examine <thing>\n"
        "  |wInventory:|n    get, drop, inventory (i), weight\n"
        "  |wEquipment:|n    wear, wield, hold, remove, equipment (eq)\n"
        "  |wFlying:|n       fly up/down (needs FLY condition)\n"
        "  |wSwimming:|n     swim up/down (WATER_BREATHING prevents drowning)\n"
        "  |wLight:|n        light <torch>, extinguish <torch>\n"
        "  |wCombat:|n       attack, dodge, flee, score, stats\n"
        "  |wEating:|n       eat <food>, hunger\n"
        "  |wDrinking:|n     drink, refill, score (thirst level)\n\n"
        "For more info on any topic, use |whelp <topic>|n.\n"
        "For a list of all help topics, use |whelp|n.\n\n"
        "|yMove |weast|y to return to the Tutorial Hub and "
        "receive your graduation reward!|n",
        guide_context=(
            "Congratulate the player! They've learned the survival basics: "
            "movement, looking, inventory, equipment, flying, swimming, "
            "light, combat, eating, and drinking. Mention |whelp <topic>|n "
            "for more info. Tell them to head |weast|n for their graduation "
            "reward. Mention Tutorials 2 (economics) and 3 (growth & social) "
            "are available from the hub."
        ),
    )
    _connect_bidirectional_exit(rooms["wellspring"], rooms["complete"], "east")
    _spawn_pip(rooms["complete"])

    # ================================================================== #
    #  Exit from Tutorial Complete back to Hub — special handling
    # ================================================================== #

    # The east exit from Room 10 goes to the hub and triggers completion.
    # This is handled by the TutorialCompletionExit.
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

    return rooms["welcome"]
