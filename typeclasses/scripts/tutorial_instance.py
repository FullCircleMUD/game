"""
TutorialInstanceScript — per-player tutorial instance manager.

Creates a private set of tutorial rooms for a single player, tracks them
via tags, and cleans up everything when the player exits.

Unlike DungeonInstanceScript, tutorial rooms are pre-built (not procedural)
and there is no time pressure — the player can take as long as they want.
"""

import uuid

from evennia import AttributeProperty, DefaultScript, create_object
from evennia.utils.search import search_tag


class TutorialInstanceScript(DefaultScript):
    """
    Manages a single player's tutorial instance.

    Lifecycle: active → collapsing → done
    """

    instance_key = AttributeProperty(None)
    character_id = AttributeProperty(None)
    hub_room_id = AttributeProperty(None)
    chunk_num = AttributeProperty(1)
    state = AttributeProperty("active")

    def at_script_creation(self):
        self.key = self.instance_key or f"tutorial_{uuid.uuid4().hex[:8]}"
        self.instance_key = self.key
        self.interval = 60  # tick every minute for orphan cleanup
        self.persistent = True
        self.start_delay = True
        self.repeats = 0

    # ------------------------------------------------------------------ #
    #  Character access
    # ------------------------------------------------------------------ #

    def get_character(self):
        """Return the character for this instance, or None."""
        if not self.character_id:
            return None
        from evennia import ObjectDB
        try:
            return ObjectDB.objects.get(id=self.character_id)
        except ObjectDB.DoesNotExist:
            return None

    @property
    def hub_room(self):
        """Return the tutorial hub room."""
        if not self.hub_room_id:
            return None
        from evennia import ObjectDB
        try:
            return ObjectDB.objects.get(id=self.hub_room_id)
        except ObjectDB.DoesNotExist:
            return None

    # ------------------------------------------------------------------ #
    #  Start tutorial
    # ------------------------------------------------------------------ #

    def start_tutorial(self, character, chunk_num=1):
        """
        Build all rooms for the given tutorial chunk and move the player in.
        """
        self.character_id = character.id
        self.chunk_num = chunk_num

        # Tag the character
        character.tags.add(self.instance_key, category="tutorial_character")

        # Build the rooms
        if chunk_num == 1:
            from world.tutorial.tutorial_1_builder import build_tutorial_1
            first_room = build_tutorial_1(self)
            title = "Tutorial 1: Survival Basics"
        elif chunk_num == 2:
            from world.tutorial.tutorial_2_builder import build_tutorial_2
            first_room = build_tutorial_2(self)
            title = "Tutorial 2: The Economic Loop"
        elif chunk_num == 3:
            from world.tutorial.tutorial_3_builder import build_tutorial_3
            first_room = build_tutorial_3(self)
            title = "Tutorial 3: Growth & Social"
        else:
            character.msg(f"|rTutorial {chunk_num} is not yet available.|n")
            return

        # Move character into first room
        # (each room has its own Pip spawned by the builder)
        character.move_to(first_room, quiet=True, move_type="teleport")
        character.msg(f"|c=== {title} ===|n")
        character.msg(first_room.db.desc or "")

    # ------------------------------------------------------------------ #
    #  Collapse / cleanup
    # ------------------------------------------------------------------ #

    def collapse_instance(self, give_reward=False):
        """
        Strip tutorial items from the player, delete all instance objects,
        and return the player to the hub.

        Args:
            give_reward: If True, give the graduation starter kit.
        """
        if self.state == "done":
            return

        self.state = "collapsing"
        char = self.get_character()

        if char:
            # Remove tutorial tag
            char.tags.remove(self.instance_key, category="tutorial_character")

            # Clear follow state (in case player followed a tutorial NPC)
            if hasattr(char, "following") and char.following:
                char.following = None

            # Strip tutorial items — unequip first (so at_remove fires and
            # conditions like fly/water_breathing are properly cleaned up),
            # then delete.
            for item in list(char.contents):
                if getattr(item.db, "tutorial_item", False):
                    if hasattr(char, "is_worn") and char.is_worn(item):
                        char.remove(item)
                    item.delete()

            # Strip any tutorial resources
            for rid in [1, 2, 3, 6, 7]:  # wheat, flour, bread, wood, timber
                amt = char.get_resource(rid) if hasattr(char, "get_resource") else 0
                if amt > 0:
                    char.return_resource_to_reserve(rid, amt)

            # Graduation reward — once per account
            if give_reward and char.account:
                self._give_graduation_reward(char)

            # Move to hub
            hub = self.hub_room
            if hub:
                char.move_to(hub, quiet=True, move_type="teleport")
                char.msg("|cYou return to the Tutorial Hub.|n")

        # Delete all tagged objects (mobs first, then items, exits, rooms)
        for category in [
            "tutorial_mob",
            "tutorial_item",
            "tutorial_exit",
            "tutorial_room",
        ]:
            for obj in search_tag(self.instance_key, category=category):
                obj.delete()

        self.state = "done"
        self.stop()
        self.delete()

    def _give_graduation_reward(self, char):
        """Give per-tutorial rewards, gated once per account."""
        if self.chunk_num == 1:
            self._reward_tutorial_1(char)
        elif self.chunk_num == 2:
            self._reward_tutorial_2(char)
        elif self.chunk_num == 3:
            self._reward_tutorial_3(char)

    def _reward_tutorial_1(self, char):
        """Tutorial 1 reward: 2 bread, 50 gold, wooden dagger."""
        account = char.account
        if getattr(account.db, "tutorial_starter_given", False):
            return
        account.db.tutorial_starter_given = True

        char.receive_resource_from_reserve(3, 2)  # 2 bread
        char.receive_gold_from_reserve(50)

        dagger = create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="a wooden training dagger",
            location=char,
            attributes=[
                ("desc", "A simple wooden dagger, suitable for a beginner."),
            ],
        )
        dagger.locks.add("get:true()")

        char.msg(
            "\n|g=== Graduation Reward! ===|n\n"
            "As a reward for completing the tutorial, you receive:\n"
            "  - 2 bread\n"
            "  - 50 gold\n"
            "  - A wooden training dagger\n"
            "|gGood luck, adventurer!|n\n"
        )

    def _reward_tutorial_2(self, char):
        """Tutorial 2 reward: 100 gold, 10 wheat, 5 wood."""
        account = char.account
        if getattr(account.db, "tutorial_2_reward_given", False):
            return
        account.db.tutorial_2_reward_given = True

        char.receive_gold_from_reserve(100)
        char.receive_resource_from_reserve(1, 10)  # 10 wheat
        char.receive_resource_from_reserve(6, 5)   # 5 wood

        char.msg(
            "\n|g=== Graduation Reward! ===|n\n"
            "As a reward for completing the economics tutorial:\n"
            "  - 100 gold\n"
            "  - 10 wheat\n"
            "  - 5 wood\n"
            "|gHappy trading, adventurer!|n\n"
        )

    def _reward_tutorial_3(self, char):
        """Tutorial 3 reward: 1 general skill point, 100 gold."""
        account = char.account
        if getattr(account.db, "tutorial_3_reward_given", False):
            return
        account.db.tutorial_3_reward_given = True

        char.receive_gold_from_reserve(100)
        # Award 1 general skill point
        current = getattr(char.db, "general_skill_points_available", 0) or 0
        char.db.general_skill_points_available = current + 1

        char.msg(
            "\n|g=== Graduation Reward! ===|n\n"
            "As a reward for completing the growth tutorial:\n"
            "  - 100 gold\n"
            "  - 1 general skill point\n"
            "|gGrow strong, adventurer!|n\n"
        )

    # ------------------------------------------------------------------ #
    #  Periodic tick — orphan cleanup
    # ------------------------------------------------------------------ #

    def at_repeat(self):
        """Check if the player has disconnected or left the tutorial."""
        if self.state == "done":
            self.stop()
            return

        char = self.get_character()
        if not char:
            # Character deleted — clean up
            self.collapse_instance()
            return

        # Check if character is still in a tutorial room
        if char.location:
            room_tags = char.location.tags.get(
                category="tutorial_room", return_list=True
            ) or []
            hub_tags = char.location.tags.get(
                category="tutorial_hub", return_list=True
            ) or []
            if not room_tags and not hub_tags:
                # Player left the tutorial zone somehow — clean up
                self.collapse_instance()
