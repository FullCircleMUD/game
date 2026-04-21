"""
TutorialInstanceScript — per-player tutorial instance manager.

Creates a private set of tutorial rooms for a single player, tracks them
via tags, and cleans up everything when the player exits.

Unlike DungeonInstanceScript, tutorial rooms are pre-built (not procedural)
and there is no time pressure — the player can take as long as they want.

Spin-up and tear-down are chunked across multiple reactor ticks via
`evennia.utils.delay` so a single tutorial entry/exit cannot freeze the
reactor for every connected player. Tests and any non-interactive caller
can force the synchronous path with `immediate=True`.
"""

import uuid

from evennia import AttributeProperty, DefaultScript, create_object
from evennia.utils import delay
from evennia.utils.search import search_tag


# Number of objects to delete per reactor tick during teardown.
_COLLAPSE_BATCH_SIZE = 8


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
    # Snapshot of character fungibles on tutorial entry — restored on exit
    snapshot_gold = AttributeProperty(None)
    snapshot_resources = AttributeProperty(None)
    # Bank snapshot (tutorial 2 only — has a bank room)
    snapshot_bank_gold = AttributeProperty(None)
    snapshot_bank_resources = AttributeProperty(None)

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

    _TITLES = {
        1: "Tutorial 1: Survival Basics",
        2: "Tutorial 2: The Economic Loop",
        3: "Tutorial 3: Growth & Social",
    }

    def start_tutorial(self, character, chunk_num=1, immediate=False):
        """
        Build all rooms for the given tutorial chunk and move the player in.

        Args:
            character: The character entering the tutorial.
            chunk_num: Which tutorial to start (1, 2, or 3).
            immediate: If True, build synchronously and teleport in one
                tick (used by tests and any non-interactive caller).
                If False (default), chunk the build across multiple
                reactor ticks with progress messages so the reactor
                stays responsive for every connected player.
        """
        self.character_id = character.id
        self.chunk_num = chunk_num

        # Tag the character
        character.tags.add(self.instance_key, category="tutorial_character")

        # Snapshot fungible balances — restored on exit so the tutorial
        # is economically neutral (graduation rewards added after restore).
        self._snapshot_fungibles(character)

        title = self._TITLES.get(chunk_num)
        if not title:
            character.msg(f"|rTutorial {chunk_num} is not yet available.|n")
            return

        if immediate:
            first_room = self._build_sync(chunk_num)
            self._on_tutorial_ready(character, first_room, title)
            return

        # Async chunked build — the entering player gets friendly progress
        # feedback while the reactor services other players between phases.
        character.ndb.tutorial_building = True
        character.msg(
            "|cSpinning up your very own tutorial instance — one moment...|n"
        )

        def _on_complete(first_room):
            character.ndb.tutorial_building = False
            self._on_tutorial_ready(character, first_room, title)

        self._build_chunked(chunk_num, character, _on_complete)

    def _build_sync(self, chunk_num):
        """Synchronous build — returns the first room."""
        if chunk_num == 1:
            from world.tutorial.tutorial_1_builder import build_tutorial_1
            return build_tutorial_1(self)
        if chunk_num == 2:
            from world.tutorial.tutorial_2_builder import build_tutorial_2
            return build_tutorial_2(self)
        if chunk_num == 3:
            from world.tutorial.tutorial_3_builder import build_tutorial_3
            return build_tutorial_3(self)
        return None

    def _build_chunked(self, chunk_num, character, on_complete):
        """Kick off the async chunked builder for this chunk_num."""
        if chunk_num == 1:
            from world.tutorial.tutorial_1_builder import build_tutorial_1_chunked
            build_tutorial_1_chunked(self, character, on_complete)
        elif chunk_num == 2:
            from world.tutorial.tutorial_2_builder import build_tutorial_2_chunked
            build_tutorial_2_chunked(self, character, on_complete)
        elif chunk_num == 3:
            from world.tutorial.tutorial_3_builder import build_tutorial_3_chunked
            build_tutorial_3_chunked(self, character, on_complete)

    def _on_tutorial_ready(self, character, first_room, title):
        """Finalise spin-up: teleport the player and show the room."""
        if character.pk is None or first_room is None:
            return
        character.move_to(first_room, quiet=True, move_type="teleport")
        character.msg(f"|c=== {title} ===|n")
        character.msg(first_room.db.desc or "")

    # ------------------------------------------------------------------ #
    #  Collapse / cleanup
    # ------------------------------------------------------------------ #

    def collapse_instance(self, give_reward=False, immediate=False):
        """
        Strip tutorial items from the player, delete all instance objects,
        and return the player to the hub.

        Args:
            give_reward: If True, give the graduation starter kit.
            immediate: If True, delete all tagged objects synchronously
                in one tick (tests / fallback). If False (default),
                chunk deletions across multiple reactor ticks so the
                reactor stays responsive.
        """
        if self.state == "done" or self.state == "collapsing":
            return

        char = self.get_character()
        if char:
            char.msg("|cWrapping up your tutorial — one moment...|n")

        self.state = "collapsing"

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

            # Restore fungible balances to pre-tutorial snapshot so the
            # tutorial is economically neutral.
            self._restore_fungibles(char)

            # Graduation reward — once per account
            if give_reward and char.account:
                self._give_graduation_reward(char)

            # Move to hub (player sees themselves back in the hub
            # immediately even while the rest of cleanup is chunked).
            hub = self.hub_room
            if hub:
                char.move_to(hub, quiet=True, move_type="teleport")
                char.msg("|cYou return to the Tutorial Hub.|n")

        # Collect objects to delete (mobs → items → exits → rooms)
        targets = []
        for category in [
            "tutorial_mob",
            "tutorial_item",
            "tutorial_exit",
            "tutorial_room",
        ]:
            for obj in search_tag(self.instance_key, category=category):
                targets.append(obj)

        if immediate or not targets:
            for obj in targets:
                obj.delete()
            self._finish_collapse()
            return

        if char:
            char.msg("|xPacking up your tutorial instance...|n")

        self._delete_in_batches(targets, 0)

    def _delete_in_batches(self, targets, index):
        """Delete tagged objects in batches, yielding to the reactor."""
        end = min(index + _COLLAPSE_BATCH_SIZE, len(targets))
        for i in range(index, end):
            try:
                targets[i].delete()
            except Exception:
                # An object may already be gone (e.g. cascade delete
                # from a room). Continue — tag lookup was a snapshot.
                pass
        if end >= len(targets):
            self._finish_collapse()
            return
        delay(0, self._delete_in_batches, targets, end)

    def _finish_collapse(self):
        """Final step: mark done and remove the managing script."""
        char = self.get_character()
        if char and char.sessions.count() > 0:
            char.msg("|xTutorial instance released.|n")

        self.state = "done"
        self.stop()
        self.delete()

    # ------------------------------------------------------------------ #
    #  Fungible snapshot / restore
    # ------------------------------------------------------------------ #

    def _snapshot_fungibles(self, char):
        """Record the character's (and optionally bank's) fungible state."""
        self.snapshot_gold = char.get_gold() if hasattr(char, "get_gold") else 0
        self.snapshot_resources = (
            char.get_all_resources()
            if hasattr(char, "get_all_resources")
            else {}
        )

        # Tutorial 2 has a bank room — snapshot bank too
        if self.chunk_num == 2 and char.account:
            bank = getattr(char.account.db, "bank", None)
            if bank:
                self.snapshot_bank_gold = (
                    bank.get_gold() if hasattr(bank, "get_gold") else 0
                )
                self.snapshot_bank_resources = (
                    bank.get_all_resources()
                    if hasattr(bank, "get_all_resources")
                    else {}
                )

    def _restore_fungibles(self, char):
        """
        Restore fungible balances to the pre-tutorial snapshot.

        Any resources gained during the tutorial are returned to reserve;
        any resources spent are received back from reserve. This makes the
        tutorial economically neutral — graduation rewards are added after.
        """
        if self.snapshot_gold is None:
            return  # no snapshot taken (shouldn't happen)

        self._restore_object_fungibles(
            char, self.snapshot_gold, self.snapshot_resources or {}
        )

        # Restore bank if we snapshotted it (tutorial 2 only)
        if self.snapshot_bank_gold is not None and char.account:
            bank = getattr(char.account.db, "bank", None)
            if bank:
                self._restore_object_fungibles(
                    bank,
                    self.snapshot_bank_gold,
                    self.snapshot_bank_resources or {},
                )

    def _restore_object_fungibles(self, obj, snap_gold, snap_resources):
        """Restore a single object's gold + resources to snapshot values."""
        # --- Gold ---
        current_gold = obj.get_gold() if hasattr(obj, "get_gold") else 0
        delta_gold = current_gold - snap_gold
        if delta_gold > 0:
            obj.return_gold_to_reserve(delta_gold)
        elif delta_gold < 0:
            obj.receive_gold_from_reserve(-delta_gold)

        # --- Resources ---
        current_resources = (
            obj.get_all_resources()
            if hasattr(obj, "get_all_resources")
            else {}
        )
        # All resource IDs that appear in either snapshot or current
        all_rids = set(snap_resources.keys()) | set(current_resources.keys())
        for rid in all_rids:
            snap_amt = snap_resources.get(rid, 0)
            curr_amt = current_resources.get(rid, 0)
            delta = curr_amt - snap_amt
            if delta > 0:
                obj.return_resource_to_reserve(rid, delta)
            elif delta < 0:
                obj.receive_resource_from_reserve(rid, -delta)

    def _give_graduation_reward(self, char):
        """Give per-tutorial rewards, gated once per account."""
        if self.chunk_num == 1:
            self._reward_tutorial_1(char)
        elif self.chunk_num == 2:
            self._reward_tutorial_2(char)
        elif self.chunk_num == 3:
            self._reward_tutorial_3(char)

    @staticmethod
    def _register_quest_debt(category, key, amount):
        """Register tutorial reward debt with the spawn system."""
        from blockchain.xrpl.services.spawn.service import get_spawn_service

        service = get_spawn_service()
        if service:
            service.allocate_quest_reward(category, key, amount)

    def _reward_tutorial_1(self, char):
        """Tutorial 1 reward: 10 gold, 2 bread."""
        account = char.account
        if getattr(account.db, "tutorial_starter_given", False):
            return
        account.db.tutorial_starter_given = True

        char.receive_gold_from_reserve(10)
        char.receive_resource_from_reserve(3, 2)  # 2 bread

        # Debt: 10 gold + upstream bread cost (2 wheat, 2 wood, 4 gold)
        self._register_quest_debt("gold", "gold", 14)
        self._register_quest_debt("resources", "1", 2)   # 2 wheat
        self._register_quest_debt("resources", "6", 2)   # 2 wood

        char.msg(
            "\n|g=== Graduation Reward! ===|n\n"
            "As a reward for completing the tutorial, you receive:\n"
            "  - 10 gold\n"
            "  - 2 bread\n"
            "|gGood luck, adventurer!|n\n"
        )

    def _reward_tutorial_2(self, char):
        """Tutorial 2 reward: 20 gold, 10 wheat, 5 wood."""
        account = char.account
        if getattr(account.db, "tutorial_2_reward_given", False):
            return
        account.db.tutorial_2_reward_given = True

        char.receive_gold_from_reserve(20)
        char.receive_resource_from_reserve(1, 10)  # 10 wheat
        char.receive_resource_from_reserve(6, 5)   # 5 wood

        self._register_quest_debt("gold", "gold", 20)
        self._register_quest_debt("resources", "1", 10)  # 10 wheat
        self._register_quest_debt("resources", "6", 5)   # 5 wood

        char.msg(
            "\n|g=== Graduation Reward! ===|n\n"
            "As a reward for completing the economics tutorial:\n"
            "  - 20 gold\n"
            "  - 10 wheat\n"
            "  - 5 wood\n"
            "|gHappy trading, adventurer!|n\n"
        )

    def _reward_tutorial_3(self, char):
        """Tutorial 3 reward: 50 gold."""
        account = char.account
        if getattr(account.db, "tutorial_3_reward_given", False):
            return
        account.db.tutorial_3_reward_given = True

        char.receive_gold_from_reserve(20)
        self._register_quest_debt("gold", "gold", 20)

        char.msg(
            "\n|g=== Graduation Reward! ===|n\n"
            "As a reward for completing the growth tutorial:\n"
            "  - 20 gold\n"
            "|gGrow strong, adventurer!|n\n"
        )

    # ------------------------------------------------------------------ #
    #  Periodic tick — orphan cleanup
    # ------------------------------------------------------------------ #

    def at_repeat(self):
        """Check if the player has disconnected or left the tutorial."""
        if self.state in ("done", "collapsing"):
            if self.state == "done":
                self.stop()
            return

        char = self.get_character()
        if not char:
            # Character deleted — clean up
            self.collapse_instance()
            return

        # If the character is still in the middle of an async build,
        # don't treat "no tutorial room yet" as an orphan.
        if getattr(char.ndb, "tutorial_building", False):
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
