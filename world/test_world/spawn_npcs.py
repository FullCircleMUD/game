"""
Spawn NPC mobs into the test world.

Run AFTER build_test_world() has created rooms.
Places trainer, guildmaster, and shopkeeper NPCs in appropriate rooms.

Usage (from Evennia):
    @py from world.test_world.spawn_npcs import spawn_npcs; spawn_npcs()
"""

from evennia import ObjectDB
from evennia.utils import create


def _find_room(key):
    """Find a room by key. Returns first match or None."""
    results = ObjectDB.objects.filter(
        db_key__iexact=key, db_typeclass_path__contains="room"
    )
    if results.exists():
        return results.first()
    results = ObjectDB.objects.filter(db_key__iexact=key)
    return results.first() if results.exists() else None


def _spawn_trainer(room_key, name, trainer_class, skills, weapons, masteries):
    """
    Spawn a TrainerNPC into the given room.

    Args:
        room_key: Room key to place the trainer in.
        name: Display name for the trainer NPC.
        trainer_class: Class key string (e.g. "warrior").
        skills: List of skill key strings this trainer teaches.
        weapons: List of weapon key strings this trainer teaches.
        masteries: Dict mapping skill/weapon key to mastery int (1-5).
    """
    room = _find_room(room_key)
    if not room:
        print(f"  [!] Room '{room_key}' not found — skipping {name}")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.trainer.TrainerNPC",
        key=name,
        location=room,
    )
    npc.trainable_skills = skills
    npc.trainable_weapons = weapons
    npc.trainer_class = trainer_class
    npc.trainer_masteries = masteries
    npc.db.desc = (
        f"{name} stands ready to train those who seek to improve their "
        f"combat skills. Type |wtrain|n to see what they can teach."
    )
    print(f"  Spawned trainer '{name}' in {room.key} ({room.dbref})")
    return npc


def _spawn_guildmaster(room_key, name, guild_class, quest_key=None,
                       max_advance_level=40, next_guildmaster_hint=None):
    """
    Spawn a GuildmasterNPC into the given room.

    Args:
        room_key: Room key to place the guildmaster in.
        name: Display name for the guildmaster NPC.
        guild_class: Class key string (e.g. "warrior").
        quest_key: Quest key required for multiclassing (None = no quest).
        max_advance_level: Highest class level this guildmaster can grant.
        next_guildmaster_hint: Flavour text pointing to the next guildmaster.
    """
    room = _find_room(room_key)
    if not room:
        print(f"  [!] Room '{room_key}' not found — skipping {name}")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.guildmaster.GuildmasterNPC",
        key=name,
        location=room,
    )
    npc.guild_class = guild_class
    npc.multi_class_quest_key = quest_key
    npc.max_advance_level = max_advance_level
    npc.next_guildmaster_hint = next_guildmaster_hint
    npc.db.desc = (
        f"{name} oversees the guild and judges those who seek membership. "
        f"Type |wguild|n for info, |wquest|n for the guild quest."
    )
    print(f"  Spawned guildmaster '{name}' in {room.key} ({room.dbref})")
    return npc


def _spawn_nft_shopkeeper(room_key, name, inventory, shop_name, desc):
    """
    Spawn an NFTShopkeeperNPC into the given room.

    Args:
        room_key: Room key to place the shopkeeper in.
        name: Display name for the NPC.
        inventory: List of str NFTItemType names this shop trades.
        shop_name: Display name for the shop (shown in list/quote output).
        desc: Description string for the NPC.
    """
    room = _find_room(room_key)
    if not room:
        print(f"  [!] Room '{room_key}' not found — skipping {name}")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.nft_shopkeeper.NFTShopkeeperNPC",
        key=name,
        location=room,
    )
    npc.inventory = inventory
    npc.shop_name = shop_name
    npc.db.desc = desc
    print(f"  Spawned NFT shopkeeper '{name}' in {room.key} ({room.dbref})")
    return npc


def _spawn_shopkeeper(room_key, name, inventory, shop_name, desc):
    """
    Spawn a ResourceShopkeeperNPC into the given room.

    Args:
        room_key: Room key to place the shopkeeper in.
        name: Display name for the shopkeeper NPC.
        inventory: List of int resource IDs this shop trades.
        shop_name: Display name for the shop (shown in list/quote output).
        desc: Description string for the NPC.
    """
    room = _find_room(room_key)
    if not room:
        print(f"  [!] Room '{room_key}' not found — skipping {name}")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.resource_shopkeeper.ResourceShopkeeperNPC",
        key=name,
        location=room,
    )
    npc.inventory = inventory
    npc.shop_name = shop_name
    npc.db.desc = desc
    print(f"  Spawned shopkeeper '{name}' in {room.key} ({room.dbref})")
    return npc


def spawn_npcs():
    """Spawn all test world NPCs."""
    print("--- Spawning NPCs ---")

    # ── Warriors Guild Trainer ──
    _spawn_trainer(
        room_key="Warriors Guild",
        name="Sergeant Grimjaw",
        trainer_class="warrior",
        skills=["bash", "riposte"],
        weapons=["long_sword", "battleaxe"],
        masteries={
            "long_sword": 5,   # GRANDMASTER
            "battleaxe": 5,    # GRANDMASTER
            "bash": 5,         # GRANDMASTER
            "riposte": 5,      # GRANDMASTER
        },
    )

    # ── Warriors Guild Guildmaster ──
    _spawn_guildmaster(
        room_key="Guildmasters Chamber",
        name="Warlord Thane",
        guild_class="warrior",
        quest_key="warrior_initiation",
        max_advance_level=40,
        next_guildmaster_hint="the War Marshal in the Capital",
    )

    # ── Thieves Guild Trainer ──
    _spawn_trainer(
        room_key="Thieves Guild Entrance",
        name="Whisper",
        trainer_class="thief",
        skills=["stealth", "subterfuge", "stab", "magical secrets"],
        weapons=["dagger", "short_sword", "rapier", "crossbow"],
        masteries={
            "dagger": 5,            # GRANDMASTER
            "short_sword": 5,       # GRANDMASTER
            "rapier": 5,            # GRANDMASTER
            "crossbow": 5,          # GRANDMASTER
            "stealth": 5,           # GRANDMASTER
            "subterfuge": 5,        # GRANDMASTER
            "stab": 5,              # GRANDMASTER
            "magical secrets": 5,   # GRANDMASTER
        },
    )

    # ── Thieves Guild Guildmaster ──
    _spawn_guildmaster(
        room_key="Thieves Guild Entrance",
        name="Shadow Mistress Vex",
        guild_class="thief",
        quest_key="thief_initiation",
        max_advance_level=40,
        next_guildmaster_hint="the Night Baron in the Capital",
    )

    # ── Mages Guild Trainer ──
    _spawn_trainer(
        room_key="Wizard's Workshop",
        name="Archmage Tindel",
        trainer_class="mage",
        skills=[
            "evocation", "conjuration", "divination",
            "abjuration", "necromancy", "illusion", "enchanting",
        ],
        weapons=["dagger", "staff"],
        masteries={
            "dagger": 5,        # GRANDMASTER
            "staff": 5,         # GRANDMASTER
            "evocation": 5,     # GRANDMASTER
            "conjuration": 5,   # GRANDMASTER
            "divination": 5,    # GRANDMASTER
            "abjuration": 5,    # GRANDMASTER
            "necromancy": 5,    # GRANDMASTER
            "illusion": 5,      # GRANDMASTER
            "enchanting": 5,    # GRANDMASTER
        },
    )

    # ── Mages Guild Guildmaster ──
    _spawn_guildmaster(
        room_key="Mages Guild Entrance",
        name="High Magus Elara",
        guild_class="mage",
        quest_key="mage_initiation",
        max_advance_level=40,
        next_guildmaster_hint="the Arcane Council in the Capital",
    )

    # ── Temple Trainer ──
    _spawn_trainer(
        room_key="Temple Sanctum",
        name="Brother Aldric",
        trainer_class="cleric",
        skills=[
            "divine_healing", "divine_protection", "divine_judgement",
            "divine_revelation", "divine_dominion", "turn_undead",
        ],
        weapons=["mace", "hammer", "staff"],
        masteries={
            "mace": 5,                # GRANDMASTER
            "hammer": 5,              # GRANDMASTER
            "staff": 5,               # GRANDMASTER
            "divine_healing": 5,      # GRANDMASTER
            "divine_protection": 5,   # GRANDMASTER
            "divine_judgement": 5,    # GRANDMASTER
            "divine_revelation": 5,   # GRANDMASTER
            "divine_dominion": 5,     # GRANDMASTER
            "turn_undead": 5,         # GRANDMASTER
        },
    )

    # ── Temple Guildmaster ──
    _spawn_guildmaster(
        room_key="Temple Entrance",
        name="High Priestess Maren",
        guild_class="cleric",
        quest_key="cleric_initiation",
        max_advance_level=40,
        next_guildmaster_hint="the Grand Cathedral in the Capital",
    )

    # ================================================================== #
    #  Production Skill Trainers (general — any class can train)
    # ================================================================== #

    # ── Blacksmith Trainer ──
    trainer = _spawn_trainer(
        room_key="blacksmith",
        name="Master Smith Braga",
        trainer_class=None,
        skills=["blacksmith"],
        weapons=[],
        masteries={"blacksmith": 5},  # GRANDMASTER
    )
    if trainer:
        trainer.db.desc = (
            "Master Smith Braga stands at a heavy anvil, inspecting a glowing "
            "blade. Years of work at the forge have left her arms thick with "
            "muscle. Type |wtrain|n to see what she can teach."
        )

    # ── Jeweller Trainer ──
    trainer = _spawn_trainer(
        room_key="Jeweller",
        name="Gemcutter Orin",
        trainer_class=None,
        skills=["jeweller"],
        weapons=[],
        masteries={"jeweller": 5},  # GRANDMASTER
    )
    if trainer:
        trainer.db.desc = (
            "Gemcutter Orin peers through a jeweller's loupe at a half-finished "
            "silver ring, turning it slowly in the lamplight. Tiny tools and "
            "polished gems cover the workbench. "
            "Type |wtrain|n to see what he can teach."
        )

    # ── Carpenter Trainer ──
    trainer = _spawn_trainer(
        room_key="Woodshop",
        name="Old Harken",
        trainer_class=None,
        skills=["carpenter"],
        weapons=[],
        masteries={"carpenter": 5},  # GRANDMASTER
    )
    if trainer:
        trainer.db.desc = (
            "Old Harken shaves curls of timber from a plank with a well-worn "
            "drawknife, pausing now and then to sight along the grain. Sawdust "
            "dusts his leather apron. "
            "Type |wtrain|n to see what he can teach."
        )

    # ── Leatherworker Trainer ──
    trainer = _spawn_trainer(
        room_key="Leathershop",
        name="Tanner Mave",
        trainer_class=None,
        skills=["leatherworker"],
        weapons=[],
        masteries={"leatherworker": 5},  # GRANDMASTER
    )
    if trainer:
        trainer.db.desc = (
            "Tanner Mave stitches a heavy leather bracer with quick, practised "
            "hands, a curved needle flashing between each pull. Hides in various "
            "stages of curing hang from the rafters. "
            "Type |wtrain|n to see what she can teach."
        )

    # ── Alchemist Trainer ──
    trainer = _spawn_trainer(
        room_key="Apothecary",
        name="Apothecary Wynn",
        trainer_class=None,
        skills=["alchemist"],
        weapons=[],
        masteries={"alchemist": 5},  # GRANDMASTER
    )
    if trainer:
        trainer.db.desc = (
            "Apothecary Wynn measures a pinch of dried moonpetal into a "
            "bubbling flask, muttering to herself as the liquid shifts colour. "
            "Shelves of labelled jars and herb bundles line every wall. "
            "Type |wtrain|n to see what she can teach."
        )

    # ── Tailor Trainer ──
    trainer = _spawn_trainer(
        room_key="Tailor",
        name="Seamstress Lira",
        trainer_class=None,
        skills=["tailor"],
        weapons=[],
        masteries={"tailor": 5},  # GRANDMASTER
    )
    if trainer:
        trainer.db.desc = (
            "Seamstress Lira works a bolt of fine cloth through a heavy loom, "
            "her foot keeping steady rhythm on the treadle. Bolts of fabric in "
            "every colour fill the shelves behind her. "
            "Type |wtrain|n to see what she can teach."
        )

    # ================================================================== #
    #  Shopkeepers
    # ================================================================== #

    # ── General Store — wheat, flour, bread ──
    _spawn_shopkeeper(
        room_key="General Store",
        name="Merchant Harlow",
        inventory=[1, 2, 3],  # Wheat, Flour, Bread
        shop_name="Harlow's General Store",
        desc=(
            "Merchant Harlow leans against the counter with an appraising eye, "
            "ready to haggle over grain, flour, and bread. His prices shift with "
            "the market — type |wlist|n to see what's on offer."
        ),
    )

    # ── Arms Dealer — Training Dagger, Training Shortsword ──
    _spawn_nft_shopkeeper(
        room_key="Arms Dealer",
        name="Grik",
        inventory=["Training Dagger", "Training Shortsword", "Training Longsword"],
        shop_name="Grik's Blades & Blunts",
        desc=(
            "A wiry goblin with a surprisingly keen business sense perches "
            "behind a counter cluttered with wooden practice weapons. He "
            "eyes you shrewdly — type |wlist|n to see what he's selling."
        ),
    )

    # ================================================================== #
    #  LLM Test NPC
    # ================================================================== #

    room = _find_room("dirt track 3")
    if room:
        npc = create.create_object(
            "typeclasses.actors.npcs.llm_roleplay_npc.LLMRoleplayNPC",
            key="Chatty",
            location=room,
        )
        npc.llm_personality = (
            "An eccentric old man who sits by the side of the road and loves "
            "to talk to anyone who passes by. Friendly, curious, a bit nosy, "
            "and full of odd stories. He speaks with a rambling, folksy manner."
        )
        npc.llm_knowledge = (
            "You live on the dirt track outside town. You've been here for years. "
            "You know the town has a blacksmith, a temple, guilds for warriors, "
            "thieves, mages, and clerics. The inn serves decent ale. "
            "You've heard rumours of strange creatures in the sewers beneath town."
        )
        npc.llm_speech_mode = "name_match"
        npc.llm_use_vector_memory = True
        npc.db.desc = (
            "A weathered old man sits cross-legged by the roadside, chewing on "
            "a long piece of grass. His bright eyes track every passerby with "
            "eager curiosity, as if hoping someone will stop and chat."
        )
        print(f"  Spawned LLM NPC 'Chatty' in {room.key} ({room.dbref})")
    else:
        print("  [!] Room 'Dirt Track' not found — skipping Chatty")

    print("--- NPC spawning complete ---")
