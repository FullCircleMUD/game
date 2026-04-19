"""
Tutorial 3 Builder — Growth & Social.

Creates a per-player instance of Tutorial 3 with 8 rooms. All objects
are tagged with the instance key for cleanup.

Room layout:
    Hub → [1] Shortcut Workshop → [2] Hall of Records
    → [3] Speaking Chamber → [4] Hall of Skills
    → [5] Training Grounds → [6] Guild Hall → [7] Companion Room
    → [8] Complete → Hub

Usage:
    Called by TutorialInstanceScript.start_tutorial(character, chunk_num=3).
    Returns the first room object.
"""

from evennia import create_object
from evennia.utils import create

from commands.room_specific_cmds.tutorial.cmdset_tutorial import CmdSetTutorial
from typeclasses.actors.npc import BaseNPC
from typeclasses.items.base_nft_item import BaseNFTItem
from typeclasses.mixins.followable import FollowableMixin
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.world_objects.base_fixture import WorldFixture
from typeclasses.world_objects.fountain_fixture import FountainFixture
from utils.exit_helpers import connect_bidirectional_exit


def _spawn_nft_item(item_type_name, location, instance_tag):
    """
    Spawn a real NFT-backed item and tag it for tutorial cleanup.

    Uses the standard NFT lifecycle: assign_to_blank_token → spawn_into.
    On tutorial collapse, item.delete() returns the token to RESERVE.
    """
    token_id = BaseNFTItem.assign_to_blank_token(item_type_name)
    obj = BaseNFTItem.spawn_into(token_id, location)
    obj.db.tutorial_item = True
    obj.tags.add(instance_tag, category="tutorial_item")
    return obj


class FollowableNPC(FollowableMixin, BaseNPC):
    """An NPC that can be followed. Used for tutorial follow practice."""
    pass


def build_tutorial_3(instance):
    """
    Build all Tutorial 3 rooms, exits, NPCs, and fixtures.

    Args:
        instance: TutorialInstanceScript managing this tutorial.

    Returns:
        The first room (Hall of Records).
    """
    tag = instance.instance_key
    rooms = {}

    # ================================================================== #
    #  Helpers
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

    def _fixture(key, location, desc):
        """Create a tagged fixture object."""
        obj = create_object(
            WorldFixture, key=key, location=location,
            attributes=[("desc", desc), ("tutorial_item", True)],
        )
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
            "You are guiding a player through Tutorial 3: Growth & Social. "
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
        and not getattr(char.account.db, "tutorial_3_entered", False)
    )

    if first_run and char.account:
        char.account.db.tutorial_3_entered = True

    # ================================================================== #
    #  ROOM 1: Shortcut Workshop — Aliases / Nicks
    # ================================================================== #

    rooms["aliases"] = _room(
        "The Shortcut Workshop",
        "A cozy workshop filled with scrolls and parchment. A large "
        "slate board dominates one wall, covered in examples of command "
        "shortcuts. A stone fountain bubbles quietly in the corner, "
        "and a practice dummy stands near the door.",
        "|wTutorial: Creating Shortcuts|n\n\n"
        "You can create personal shortcuts for any command using "
        "|walias|n.\n\n"
        "|wSimple shortcut:|n\n"
        "  |walias sc score|n — now typing |wsc|n runs |wscore|n.\n\n"
        "|wShortcut with a target:|n\n"
        "  |walias di diagnose $1|n — |wdi dummy|n runs "
        "|wdiagnose dummy|n.\n"
        "  |w$1|n is replaced by whatever you type after the shortcut.\n\n"
        "|wMulti-command shortcut:|n (the real power!)\n"
        "  |walias dc get canteen from backpack;drink canteen;"
        "put canteen in backpack|n\n"
        "  Now |wdc|n does all three actions at once!\n\n"
        "|wManage your shortcuts:|n\n"
        "  |walias/list|n — see all your shortcuts\n"
        "  |walias/delete <name>|n — remove a shortcut\n\n"
        "|yPractice:|n\n"
        "  Pick up the |wbackpack|n and |wcanteen|n from the room.\n"
        "  Try creating and using each shortcut above.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach the alias/nick system. The |walias|n command lets "
            "players create personal shortcuts. Simple: |walias sc score|n. "
            "With args: |walias di diagnose $1|n where $1 is replaced by "
            "whatever they type after. Multi-command with semicolons: "
            "|walias dc get canteen from backpack;drink canteen;"
            "put canteen in backpack|n chains three actions into one. "
            "|walias/list|n shows all aliases, |walias/delete <name>|n "
            "removes one. There's a backpack, canteen, fountain, and "
            "practice dummy in the room for them to experiment with. "
            "Encourage them to try all three patterns."
        ),
    )

    _spawn_pip(rooms["aliases"])

    # Slate board fixture with examples
    board = _fixture(
        "a slate board", rooms["aliases"],
        "The slate board is covered in example shortcuts:\n\n"
        "  |walias sc score|n — simple shortcut\n"
        "  |walias di diagnose $1|n — shortcut with a target\n"
        "  |walias dc get canteen from backpack;drink canteen;"
        "put canteen in backpack|n — multi-command\n"
        "  |walias fc get canteen from backpack;refill canteen;"
        "put canteen in backpack|n — refill version\n\n"
        "  |walias/list|n — view your shortcuts\n"
        "  |walias/delete <name>|n — remove one",
    )
    board.aliases.add("board")
    board.aliases.add("slate board")
    board.aliases.add("slate")

    # Fountain for refill practice
    fountain = create_object(
        FountainFixture,
        key="a stone fountain",
        location=rooms["aliases"],
        attributes=[
            ("desc",
             "A small stone fountain bubbles with clear water. You "
             "could refill a water container here with |wrefill canteen fountain|n."),
        ],
    )
    fountain.db.tutorial_item = True
    fountain.tags.add(tag, category="tutorial_item")
    fountain.aliases.add("fountain")

    # Practice dummy for diagnose
    dummy = create_object(
        BaseNPC,
        key="a practice dummy",
        location=rooms["aliases"],
        attributes=[
            ("desc",
             "A straw-stuffed practice dummy. Try |wdiagnose dummy|n "
             "to inspect it, or create a shortcut: |walias di diagnose $1|n "
             "then use |wdi dummy|n."),
        ],
    )
    dummy.tags.add(tag, category="tutorial_mob")
    dummy.aliases.add("dummy")
    dummy.aliases.add("practice dummy")

    # Backpack and canteen for multi-command practice
    _spawn_nft_item("Backpack", rooms["aliases"], tag)
    _spawn_nft_item("Canteen", rooms["aliases"], tag)

    # ================================================================== #
    #  ROOM 2: Hall of Records — Score, Stats, Conditions
    # ================================================================== #

    rooms["records"] = _room(
        "Hall of Records",
        "Tall bookshelves line the walls of this grand hall, filled "
        "with ledgers and records of adventurers past. A large ornate "
        "mirror dominates one wall, and a writing desk sits nearby.",
        "|wTutorial: Character Information|n\n\n"
        "  |wscore|n — Your character summary: class, level, XP.\n"
        "  |wstats|n — Detailed statistics: HP, abilities, AC, combat.\n"
        "  |whunger|n — Check how hungry you are.\n"
        "  |wweight|n — Carrying capacity and encumbrance.\n"
        "  |wwhere|n — See where you are in the world.\n"
        "  |wquests|n — View your active and completed quests.\n"
        "  |wlanguages|n — Languages you can speak.\n\n"
        "|yPractice:|n\n"
        "  Try |wscore|n to see your character overview.\n"
        "  Try |wstats|n for detailed stats.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach character information commands. |wscore|n shows class, "
            "level, and XP. |wstats|n shows HP, abilities, AC, and combat "
            "modifiers. |wconditions|n shows active effects and resistances. "
            "Suggest they try each command to see their character details."
        ),
    )

    _spawn_pip(rooms["records"])

    # Mirror fixture
    mirror = _fixture(
        "a large ornate mirror", rooms["records"],
        "You gaze into the mirror and see your reflection staring back. "
        "Every scar, every line tells a story. Try |wscore|n to see "
        "who you really are.",
    )
    mirror.aliases.add("mirror")

    _connect_bidirectional_exit(rooms["aliases"], rooms["records"], "east")

    # ================================================================== #
    #  ROOM 3: Speaking Chamber — Communication
    # ================================================================== #

    rooms["speaking"] = _room(
        "The Speaking Chamber",
        "An acoustically perfect chamber with curved stone walls. "
        "A message board hangs near the entrance, and speaking tubes "
        "run along the ceiling to distant rooms.",
        "|wTutorial: Communication|n\n\n"
        "  |wsay <message>|n — Speak to everyone in the room.\n"
        "  |wwhisper <target> = <message>|n — Private message to someone.\n"
        "  |wshout <message>|n — Yell loudly (adjacent rooms hear muffled).\n\n"
        "Languages:\n"
        "  |wsay/dwarven hello|n — Speak in a specific language.\n"
        "  Others who don't know the language hear garbled speech.\n\n"
        "|yPractice:|n\n"
        "  Try |wsay Hello!|n to speak aloud.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach communication. |wsay <msg>|n speaks to the room. "
            "|wwhisper <target> = <msg>|n is private. |wshout <msg>|n "
            "reaches adjacent rooms (muffled). Mention language switching "
            "with |wsay/dwarven hello|n — others who don't know the "
            "language hear garbled text."
        ),
    )
    _connect_bidirectional_exit(rooms["records"], rooms["speaking"], "east")

    _spawn_pip(rooms["speaking"])

    # Message board fixture
    board = _fixture(
        "a message board", rooms["speaking"],
        "The board lists communication commands:\n\n"
        "  |wsay|n — Room speech\n"
        "  |wwhisper|n — Private message\n"
        "  |wshout|n — Loud, heard in adjacent rooms\n"
        "  Languages — switch with |wsay/<language>|n",
    )
    board.aliases.add("board")
    board.aliases.add("message board")

    # ================================================================== #
    #  ROOM 4: Hall of Skills — Skill system
    # ================================================================== #

    rooms["skills"] = _room(
        "Hall of Skills",
        "Display cases line the walls, each showcasing a different "
        "craft or discipline. A thick tome rests on a pedestal in "
        "the center of the room, its pages open to a chapter on mastery.",
        "|wTutorial: Skills|n\n\n"
        "  |wskills|n — View your skill pools and mastery levels.\n\n"
        "Three skill pools:\n"
        "  |wGeneral|n — Available to all classes (blacksmith, etc.)\n"
        "  |wClass|n — Specific to your class (warrior, mage, etc.)\n"
        "  |wWeapon|n — Proficiency with weapon types\n\n"
        "Mastery levels:\n"
        "  UNSKILLED → BASIC → SKILLED → EXPERT → MASTER → GRANDMASTER\n\n"
        "Skill points are earned when you level up.\n\n"
        "|yPractice:|n\n"
        "  Try |wskills|n to see your current skills.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach the |wskills|n command. Explain three pools: general "
            "(any class), class (specific to their class), and weapon "
            "(proficiency with weapon types). Mastery levels go from "
            "UNSKILLED to GRANDMASTER. Skill points are earned at level "
            "up and spent at trainers."
        ),
    )
    _connect_bidirectional_exit(rooms["speaking"], rooms["skills"], "east")

    _spawn_pip(rooms["skills"])

    # Skill tome fixture
    tome = _fixture(
        "a thick skill tome", rooms["skills"],
        "The tome is open to a chapter titled 'The Path of Mastery':\n\n"
        "  UNSKILLED → BASIC → SKILLED → EXPERT → MASTER → GRANDMASTER\n\n"
        "Each rank improves your ability with that skill. Train at a "
        "trainer to advance your mastery. Higher mastery means better "
        "success rates and more powerful effects.",
    )
    tome.aliases.add("tome")
    tome.aliases.add("skill tome")

    # ================================================================== #
    #  ROOM 5: Training Grounds — Training skills
    # ================================================================== #

    rooms["training"] = _room(
        "The Training Grounds",
        "A practice yard with padded training dummies and weapon racks. "
        "Instructor Bren stands in the center, arms crossed, watching "
        "newcomers with an evaluating eye.",
        "|wTutorial: Training|n\n\n"
        "  |wtrain|n — See what this trainer can teach and costs.\n"
        "  |wtrain <skill>|n — Attempt to train a specific skill.\n\n"
        "Training costs gold and a skill point. Success depends on "
        "the gap between your current mastery and the trainer's. "
        "Higher-mastery trainers give better success rates.\n\n"
        "If training fails, there's a brief cooldown before retrying.\n\n"
        "|yPractice:|n\n"
        "  Type |wtrain|n to see available skills.\n"
        "  Try |wtrain blacksmith|n to learn basic blacksmithing.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach training. |wtrain|n shows what the trainer offers "
            "and costs. |wtrain <skill>|n spends a skill point + gold "
            "to learn. Success rate depends on mastery gap — higher "
            "mastery trainers give better odds. They got a free skill "
            "point and gold for this. Suggest trying |wtrain blacksmith|n."
        ),
    )
    _connect_bidirectional_exit(rooms["skills"], rooms["training"], "east")

    _spawn_pip(rooms["training"])

    # Trainer NPC
    trainer = create.create_object(
        "typeclasses.actors.npcs.trainer.TrainerNPC",
        key="Instructor Bren",
        location=rooms["training"],
    )
    trainer.trainable_skills = ["blacksmith", "carpenter", "alchemist"]
    trainer.trainable_weapons = []
    trainer.trainer_class = None  # General skills — any class can train
    trainer.trainer_masteries = {
        "blacksmith": 3,   # EXPERT
        "carpenter": 3,    # EXPERT
        "alchemist": 3,    # EXPERT
    }
    trainer.db.desc = (
        "Instructor Bren is a stocky veteran with calloused hands and "
        "a no-nonsense demeanor. She's trained countless adventurers in "
        "the basics of crafting. Type |wtrain|n to see what she teaches."
    )
    trainer.tags.add(tag, category="tutorial_mob")

    # ================================================================== #
    #  ROOM 6: Guild Hall — Guilds and advancement
    # ================================================================== #

    rooms["guild"] = _room(
        "The Guild Hall",
        "Banners bearing the emblems of the great guilds hang from the "
        "rafters of this grand hall. Guild Warden Aldric stands beside "
        "a stone lectern, reviewing membership records.",
        "|wTutorial: Guilds & Advancement|n\n\n"
        "  |wguild|n — View your class info and requirements.\n"
        "  |wadvance|n — Level up at a guildmaster (spend earned levels).\n"
        "  |wquest|n — View guild quest for multiclassing.\n\n"
        "Your starting class was chosen during character creation. "
        "Levels are earned through XP, then spent at a guildmaster "
        "to advance your class level.\n\n"
        "Multiclassing is possible through guild quests — complete a "
        "quest to join a second class.\n\n"
        "|yPractice:|n\n"
        "  Type |wguild|n to see your class information.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach guilds and advancement. |wguild|n shows class info. "
            "|wadvance|n levels up at a guildmaster — levels are earned "
            "through XP then spent here. |wquest|n shows guild quests "
            "for multiclassing. Their starting class was chosen at "
            "character creation."
        ),
    )
    _connect_bidirectional_exit(rooms["training"], rooms["guild"], "east")

    _spawn_pip(rooms["guild"])

    # Guildmaster NPC
    guildmaster = create.create_object(
        "typeclasses.actors.npcs.guildmaster.GuildmasterNPC",
        key="Guild Warden Aldric",
        location=rooms["guild"],
    )
    guildmaster.guild_class = "warrior"
    guildmaster.max_advance_level = 5
    guildmaster.multi_class_quest_key = None
    guildmaster.db.desc = (
        "Guild Warden Aldric is a tall, grizzled man in ceremonial armour. "
        "He oversees guild membership and advancement. Type |wguild|n for "
        "class info, or |wquest|n for guild quests."
    )
    guildmaster.tags.add(tag, category="tutorial_mob")

    # ================================================================== #
    #  ROOM 7: Companion Room — Following and groups
    # ================================================================== #

    rooms["companion"] = _room(
        "The Companion Room",
        "A comfortable waiting area with padded benches and a practice "
        "track running around the perimeter. A young squire named Finn "
        "practices forms with a wooden sword, pausing to wave at you.",
        "|wTutorial: Following & Groups|n\n\n"
        "  |wfollow <player>|n — Follow someone through exits.\n"
        "  |wgroup|n — See your group members.\n"
        "  |wunfollow|n — Stop following.\n"
        "  |wnofollow|n — Toggle whether others can follow you.\n\n"
        "When following someone, you auto-move when they move.\n"
        "Groups share combat — when one member fights, the group helps.\n\n"
        "|yPractice:|n\n"
        "  Try |wfollow Finn|n to follow the squire.\n"
        "  Type |wgroup|n to see your group.\n"
        "  Type |wunfollow|n to stop.\n"
        "  Move |weast|n when ready.",
        guide_context=(
            "Teach following and groups. |wfollow <player>|n follows "
            "someone through exits automatically. |wgroup|n shows group "
            "members. |wunfollow|n stops following. |wnofollow|n toggles "
            "follow permission. Groups share combat. Suggest they try "
            "|wfollow Finn|n and then |wgroup|n to see the display."
        ),
    )
    _connect_bidirectional_exit(rooms["guild"], rooms["companion"], "east")

    _spawn_pip(rooms["companion"])

    # Companion NPC — followable mob for follow practice
    companion = create.create_object(
        FollowableNPC,
        key="Squire Finn",
        location=rooms["companion"],
    )
    companion.db.desc = (
        "A lanky young squire with unruly hair and an eager grin. He "
        "practices sword forms with exaggerated enthusiasm, occasionally "
        "tripping over his own feet."
    )
    companion.tags.add(tag, category="tutorial_mob")

    # ================================================================== #
    #  ROOM 8: Tutorial Complete
    # ================================================================== #

    rooms["complete"] = _room(
        "Tutorial Complete",
        "A bright archway glows at the end of this final chamber. "
        "Inscribed on the wall is a summary of the growth and social "
        "skills you've learned.",
        "|wTutorial 3 Complete!|n\n\n"
        "You've learned about growth and social systems:\n\n"
        "  |wAliases:|n        alias (personal shortcuts, multi-command)\n"
        "  |wCharacter Info:|n  score, stats, conditions\n"
        "  |wCommunication:|n  say, whisper, shout, languages\n"
        "  |wSkills:|n         skills (3 pools, mastery levels)\n"
        "  |wTraining:|n       train, train <skill>\n"
        "  |wGuilds:|n         guild, advance, quest\n"
        "  |wGroups:|n         follow, group, unfollow, nofollow\n\n"
        "You're ready for the world! Head east for your reward.\n\n"
        "|yTip:|n Type |whelp|n at any time to see all available "
        "commands, or |whelp <command>|n for details on a specific one.\n\n"
        "|yMove |weast|y to return to the Tutorial Hub and "
        "receive your graduation reward!|n",
        guide_context=(
            "Congratulate the player! They've learned aliases, character info, "
            "communication, skills, training, guilds, and groups. They're "
            "ready for the real world. Tell them |weast|n takes them to "
            "the hub for their reward. Wish them well!"
        ),
    )
    _connect_bidirectional_exit(rooms["companion"], rooms["complete"], "east")
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

    return rooms["aliases"]
