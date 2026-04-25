"""
Tests for character death mechanics — corpse creation, double-death guard,
defeat path, purgatory fallback, dungeon corpse recovery, and corpse
lifecycle hooks (recovery confirmation + decay closure).

evennia test --settings settings tests.typeclass_tests.test_character_death
"""

from unittest.mock import patch, MagicMock

from evennia import create_object
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from typeclasses.world_objects.corpse import Corpse


# ------------------------------------------------------------------ #
#  Dungeon test fixtures (shared by dungeon-related test classes)
# ------------------------------------------------------------------ #

def _test_room_generator(instance, depth, coords):
    """Generate a simple test dungeon room."""
    from typeclasses.terrain.rooms.dungeon.dungeon_room import DungeonRoom

    room = create_object(DungeonRoom, key=f"Test Dungeon Room d{depth}")
    room.db.desc = f"A test room at depth {depth}, coords {coords}."
    return room


def _make_test_template(template_id="test_recovery_dungeon",
                        name="Test Recovery Dungeon"):
    """Build a dungeon template suitable for defeat / recovery tests."""
    from world.dungeons.dungeon_template import DungeonTemplate

    return DungeonTemplate(
        template_id=template_id,
        name=name,
        dungeon_type="instance",
        instance_mode="solo",
        boss_depth=2,
        max_unexplored_exits=2,
        max_new_exits_per_room=2,
        instance_lifetime_seconds=7200,
        room_generator=_test_room_generator,
        boss_generator=None,
        allow_combat=True,
        allow_pvp=False,
        allow_death=False,
    )


def _setup_dungeon_room(instance, room):
    """Tag a room as a dungeon room for `instance` so it passes is_dungeon
    detection in `_defeat`."""
    room.tags.add(instance.instance_key, category="dungeon_room")
    room.dungeon_instance_id = instance.id


class TestCharacterDeath(EvenniaTest):
    """Test full death path — corpse, items, gold, XP penalty."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.experience_points = 1000
        self.char1.hp = 0
        self.room1.allow_combat = True
        self.room1.allow_death = True

    def _find_corpse(self, room):
        for obj in room.contents:
            if isinstance(obj, Corpse):
                return obj
        return None

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_die_creates_corpse(self, mock_char_delay, mock_corpse_delay):
        """Character death creates a corpse in the room."""
        self.char1.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertIsNotNone(corpse)
        self.assertEqual(corpse.key, "corpse")

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_corpse_owner_locked(self, mock_char_delay, mock_corpse_delay):
        """Character corpse starts locked with correct owner."""
        self.char1.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertFalse(corpse.is_unlocked)
        self.assertEqual(corpse.owner_character_key, self.char1.key)

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_xp_penalty_applied(self, mock_char_delay, mock_corpse_delay):
        """Death applies 5% XP penalty."""
        self.char1.experience_points = 1000
        self.char1.die("combat")
        self.assertEqual(self.char1.experience_points, 950)

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_hp_reset_to_one(self, mock_char_delay, mock_corpse_delay):
        """HP resets to 1 after death."""
        self.char1.die("combat")
        self.assertEqual(self.char1.hp, 1)

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_double_death_one_corpse(self, mock_char_delay, mock_corpse_delay):
        """Calling die() twice creates only one corpse."""
        self.char1.die("combat")
        self.char1.die("combat")  # should be no-op
        corpses = [obj for obj in self.room1.contents if isinstance(obj, Corpse)]
        self.assertEqual(len(corpses), 1)

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_double_death_single_xp_penalty(self, mock_char_delay, mock_corpse_delay):
        """Double death only applies XP penalty once."""
        self.char1.experience_points = 1000
        self.char1.die("combat")
        self.char1.die("combat")
        # 5% of 1000 = 50, applied once = 950
        self.assertEqual(self.char1.experience_points, 950)

    @patch("typeclasses.world_objects.corpse.delay")
    @patch("typeclasses.actors.character.delay")
    def test_no_purgatory_sends_home(self, mock_char_delay, mock_corpse_delay):
        """Without a purgatory room, character goes directly home."""
        home_room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Home",
        )
        self.char1.home = home_room
        self.char1.die("combat")
        self.assertEqual(self.char1.location, home_room)


class TestCharacterDefeat(EvenniaTest):
    """Test defeat path — no item loss, effects cleared."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.experience_points = 1000
        self.char1.hp = 0
        self.room1.allow_combat = True
        self.room1.allow_death = False  # defeat room

    @patch("typeclasses.world_objects.corpse.delay")
    def test_defeat_keeps_items(self, mock_delay):
        """Defeat path does not transfer items to corpse."""
        item = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="a sword",
            location=self.char1,
        )
        self.char1.die("combat")
        self.assertIn(item, self.char1.contents)

    @patch("typeclasses.world_objects.corpse.delay")
    def test_defeat_keeps_xp(self, mock_delay):
        """Defeat path does not apply XP penalty."""
        self.char1.die("combat")
        self.assertEqual(self.char1.experience_points, 1000)

    @patch("typeclasses.world_objects.corpse.delay")
    def test_defeat_clears_effects(self, mock_delay):
        """Defeat path strips all effects."""
        with patch.object(self.char1, "clear_all_effects") as mock_clear:
            self.char1.die("combat")
            mock_clear.assert_called_once()

    @patch("typeclasses.world_objects.corpse.delay")
    def test_defeat_resets_hp(self, mock_delay):
        """Defeat resets HP to 1."""
        self.char1.die("combat")
        self.assertEqual(self.char1.hp, 1)

    @patch("typeclasses.world_objects.corpse.delay")
    def test_defeat_no_pending_tag_in_static_room(self, mock_delay):
        """Static no-death room defeat does not add a dungeon_pending tag."""
        self.char1.die("combat")
        pending = self.char1.tags.get(category="dungeon_pending")
        self.assertIsNone(pending)


# ============================================================== #
#  Dungeon defeat — inventory transfer, tag flip, recovery flow
# ============================================================== #

class TestDungeonDefeat(EvenniaTest):
    """Test defeat in a procedural-dungeon room — full inventory transfer,
    corpse tagged dungeon_corpse, character tag flips to dungeon_pending.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from world.dungeons import DUNGEON_REGISTRY, register_dungeon
        from typeclasses.scripts.dungeon_instance import DungeonInstanceScript

        self.char1.experience_points = 1000
        self.char1.hp = 0
        self.room1.allow_combat = True
        self.room1.allow_death = False  # routes through _defeat

        # Register a clean test template
        DUNGEON_REGISTRY.clear()
        self.template = _make_test_template()
        register_dungeon(self.template)

        # Build a real instance and tag room1 as one of its dungeon rooms
        self.instance = create.create_script(
            DungeonInstanceScript,
            key="test_recovery_dungeon_inst1",
            autostart=False,
        )
        self.instance.template_id = self.template.template_id
        self.instance.instance_key = "test_recovery_dungeon_inst1"
        self.instance.entrance_room_id = self.room2.id
        self.instance.start()

        _setup_dungeon_room(self.instance, self.room1)

        # Tag char1 as currently inside (so the defeat flow can scrub it)
        self.char1.tags.add(
            self.instance.instance_key, category="dungeon_character"
        )

    def tearDown(self):
        try:
            if self.instance and self.instance.pk:
                self.instance.collapse_instance()
        except Exception:
            pass
        super().tearDown()

    def _find_corpse(self, room):
        for obj in room.contents:
            if isinstance(obj, Corpse):
                return obj
        return None

    @patch("typeclasses.world_objects.corpse.delay")
    def test_dungeon_defeat_transfers_nft_to_corpse(self, mock_delay):
        """NFT items in inventory transfer to the corpse on dungeon defeat."""
        from typeclasses.items.base_nft_item import BaseNFTItem

        item = create_object(BaseNFTItem, key="a sword", location=self.char1)
        self.char1.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertIsNotNone(corpse)
        self.assertIn(item, corpse.contents)
        self.assertNotIn(item, self.char1.contents)

    @patch("typeclasses.world_objects.corpse.delay")
    def test_dungeon_defeat_tags_corpse_dungeon_corpse(self, mock_delay):
        """Corpse is tagged dungeon_corpse=instance_key on dungeon defeat."""
        self.char1.die("combat")
        corpse = self._find_corpse(self.room1)
        self.assertEqual(
            corpse.tags.get(category="dungeon_corpse"),
            self.instance.instance_key,
        )

    @patch("typeclasses.world_objects.corpse.delay")
    def test_dungeon_defeat_replaces_character_tag_with_pending(self, mock_delay):
        """Character's dungeon_character tag flips to dungeon_pending."""
        self.char1.die("combat")
        self.assertIsNone(self.char1.tags.get(category="dungeon_character"))
        self.assertEqual(
            self.char1.tags.get(category="dungeon_pending"),
            self.instance.instance_key,
        )

    @patch("typeclasses.world_objects.corpse.delay")
    def test_dungeon_defeat_message_includes_dungeon_name(self, mock_delay):
        """Defeat message names the dungeon for player orientation."""
        with patch.object(self.char1, "msg") as mock_msg:
            self.char1.die("combat")
            messages = " ".join(
                str(call.args[0]) for call in mock_msg.call_args_list
                if call.args and isinstance(call.args[0], str)
            )
            self.assertIn(self.template.name, messages)

    @patch("typeclasses.world_objects.corpse.delay")
    def test_dungeon_defeat_template_missing_falls_back(self, mock_delay):
        """If instance lookup fails mid-defeat, fall back to legacy
        empty-corpse flow rather than crash. Inventory stays on character."""
        from typeclasses.items.base_nft_item import BaseNFTItem

        # Delete the instance script so the lookup misses
        instance_id = self.instance.id
        self.instance.delete()

        # The room still has the dungeon_room tag — defeat will detect it
        # and try to look up the now-missing instance.
        item = create_object(BaseNFTItem, key="a stick", location=self.char1)
        self.char1.die("combat")
        # Item stays on character in the legacy fallback flow
        self.assertIn(item, self.char1.contents)
        # No dungeon_pending tag added
        self.assertIsNone(self.char1.tags.get(category="dungeon_pending"))


# ============================================================== #
#  Corpse lifecycle hooks — recovery + decay messages, pending scrub
# ============================================================== #

class TestCorpseLifecycleHooks(EvenniaTest):
    """Test universal Corpse hooks — recovery confirmation and decay
    closure messages, plus dungeon-specific pending-tag scrub layered on top.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # A corpse owned by char1
        self.corpse = create_object(Corpse, key="corpse", location=self.room1)
        self.corpse.owner_character_key = self.char1.key
        self.corpse.owner_name = self.char1.key

    @patch("typeclasses.world_objects.corpse.delay")
    def test_at_object_leave_owner_full_loot_message(self, mock_delay):
        """Owner taking last item from corpse sees recovery confirmation."""
        from typeclasses.items.base_nft_item import BaseNFTItem

        item = create_object(BaseNFTItem, key="a sword", location=self.corpse)
        with patch.object(self.char1, "msg") as mock_msg:
            item.move_to(self.char1, quiet=True, move_type="get")
            messages = " ".join(
                str(call.args[0]) for call in mock_msg.call_args_list
                if call.args and isinstance(call.args[0], str)
            )
            self.assertIn("recovered everything", messages)

    @patch("typeclasses.world_objects.corpse.delay")
    def test_at_object_leave_non_owner_no_recovery_message(self, mock_delay):
        """A non-owner emptying the corpse does not trigger the owner's
        recovery message."""
        from typeclasses.items.base_nft_item import BaseNFTItem

        item = create_object(BaseNFTItem, key="a sword", location=self.corpse)
        with patch.object(self.char1, "msg") as mock_msg:
            # char2 is the looter, not the owner
            item.move_to(self.char2, quiet=True, move_type="get")
            messages = [
                str(call.args[0]) for call in mock_msg.call_args_list
                if call.args and isinstance(call.args[0], str)
            ]
            for m in messages:
                self.assertNotIn("recovered everything", m)

    @patch("typeclasses.world_objects.corpse.delay")
    def test_at_object_leave_partial_no_message(self, mock_delay):
        """Partial loot (corpse not yet empty) does not fire the recovery
        confirmation."""
        from typeclasses.items.base_nft_item import BaseNFTItem

        item1 = create_object(BaseNFTItem, key="a sword", location=self.corpse)
        item2 = create_object(BaseNFTItem, key="a shield", location=self.corpse)
        with patch.object(self.char1, "msg") as mock_msg:
            item1.move_to(self.char1, quiet=True, move_type="get")
            messages = [
                str(call.args[0]) for call in mock_msg.call_args_list
                if call.args and isinstance(call.args[0], str)
            ]
            for m in messages:
                self.assertNotIn("recovered everything", m)
        # item2 still in corpse
        self.assertIn(item2, self.corpse.contents)

    @patch("typeclasses.world_objects.corpse.delay")
    def test_at_object_leave_dungeon_corpse_scrubs_pending(self, mock_delay):
        """Last item leaving a dungeon_corpse-tagged corpse scrubs the
        owner's matching dungeon_pending tag."""
        from typeclasses.items.base_nft_item import BaseNFTItem

        instance_key = "scrub_test_instance"
        self.corpse.tags.add(instance_key, category="dungeon_corpse")
        self.char1.tags.add(instance_key, category="dungeon_pending")

        item = create_object(BaseNFTItem, key="a sword", location=self.corpse)
        item.move_to(self.char1, quiet=True, move_type="get")

        self.assertIsNone(self.char1.tags.get(category="dungeon_pending"))

    @patch("typeclasses.world_objects.corpse.delay")
    def test_at_object_delete_owned_corpse_decay_message(self, mock_delay):
        """Deleting an owned corpse sends the decay message to the owner."""
        with patch.object(self.char1, "msg") as mock_msg:
            self.corpse.delete()
            messages = " ".join(
                str(call.args[0]) for call in mock_msg.call_args_list
                if call.args and isinstance(call.args[0], str)
            )
            self.assertIn("decayed", messages)

    @patch("typeclasses.world_objects.corpse.delay")
    def test_at_object_delete_dungeon_corpse_scrubs_pending(self, mock_delay):
        """Deleting a dungeon_corpse-tagged corpse scrubs the matching
        dungeon_pending tag on the owner."""
        instance_key = "scrub_test_decay_instance"
        self.corpse.tags.add(instance_key, category="dungeon_corpse")
        self.char1.tags.add(instance_key, category="dungeon_pending")

        self.corpse.delete()

        self.assertIsNone(self.char1.tags.get(category="dungeon_pending"))

    @patch("typeclasses.world_objects.corpse.delay")
    def test_at_object_delete_non_dungeon_no_tag_touch(self, mock_delay):
        """Deleting a non-dungeon corpse does not touch any unrelated tags
        on the owner."""
        # Owner has an unrelated pending tag from elsewhere
        self.char1.tags.add(
            "unrelated_instance_xyz", category="dungeon_pending"
        )
        self.corpse.delete()
        # Unrelated tag still present
        self.assertEqual(
            self.char1.tags.get(category="dungeon_pending"),
            "unrelated_instance_xyz",
        )

    @patch("typeclasses.world_objects.corpse.delay")
    def test_at_object_delete_unknown_owner_silent(self, mock_delay):
        """Deleting a corpse whose owner_character_key matches no character
        does not raise."""
        self.corpse.owner_character_key = "no_such_character"
        # Should not raise
        self.corpse.delete()


# ============================================================== #
#  Entry redirect — pending tag drives re-entry into existing instance
# ============================================================== #

class TestEnterDungeonRedirect(EvenniaTest):
    """Test the pending-tag entry redirect in ProceduralDungeonMixin."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from evennia import create_object as ev_create_object
        from world.dungeons import DUNGEON_REGISTRY, register_dungeon
        from typeclasses.scripts.dungeon_instance import DungeonInstanceScript
        from typeclasses.terrain.exits.procedural_dungeon_exit import (
            ProceduralDungeonExit,
        )

        DUNGEON_REGISTRY.clear()
        self.template = _make_test_template()
        register_dungeon(self.template)

        # Real instance with one room at (0,0)
        self.instance = create.create_script(
            DungeonInstanceScript,
            key="test_recovery_dungeon_redirect_inst",
            autostart=False,
        )
        self.instance.template_id = self.template.template_id
        self.instance.instance_key = "test_recovery_dungeon_redirect_inst"
        self.instance.entrance_room_id = self.room1.id
        self.instance.start()

        # Build an alive instance with room (0,0) populated
        from typeclasses.terrain.rooms.dungeon.dungeon_room import DungeonRoom

        self.dungeon_room = ev_create_object(
            DungeonRoom, key="Recovery Test Room"
        )
        self.dungeon_room.tags.add(
            self.instance.instance_key, category="dungeon_room"
        )
        self.dungeon_room.dungeon_instance_id = self.instance.id
        self.instance.db.xy_grid = {(0, 0): self.dungeon_room.id}

        # Build the entrance exit (its at_traverse will call enter_dungeon)
        self.entrance = ev_create_object(
            ProceduralDungeonExit,
            key="north",
            location=self.room1,
            destination=self.room1,  # self-referential — will be resolved
        )
        self.entrance.dungeon_template_id = self.template.template_id

    def tearDown(self):
        try:
            if self.instance and self.instance.pk:
                self.instance.collapse_instance()
        except Exception:
            pass
        super().tearDown()

    def test_pending_match_redirects_to_room_zero(self):
        """A pending tag matching the entrance's template redirects the
        player into room (0,0) of the existing instance."""
        self.char1.tags.add(
            self.instance.instance_key, category="dungeon_pending"
        )
        result = self.entrance.enter_dungeon(self.char1)
        self.assertTrue(result)
        self.assertEqual(self.char1.location, self.dungeon_room)

    def test_pending_match_keeps_pending_tag_adds_character_tag(self):
        """After redirect, both tags coexist — pending stays until corpse
        is fully looted or decays; character tag tracks current presence."""
        self.char1.tags.add(
            self.instance.instance_key, category="dungeon_pending"
        )
        self.entrance.enter_dungeon(self.char1)
        self.assertEqual(
            self.char1.tags.get(category="dungeon_pending"),
            self.instance.instance_key,
        )
        self.assertEqual(
            self.char1.tags.get(category="dungeon_character"),
            self.instance.instance_key,
        )

    def test_pending_stale_scrubbed_proceeds(self):
        """A pending tag pointing at a non-existent instance is scrubbed
        silently and the redirect returns False (caller falls through)."""
        self.char1.tags.add(
            "nonexistent_instance_key", category="dungeon_pending"
        )
        result = self.entrance._try_pending_recovery_redirect(
            self.char1, self.template
        )
        self.assertFalse(result)
        self.assertIsNone(self.char1.tags.get(category="dungeon_pending"))

    def test_different_template_falls_through(self):
        """A pending tag for a different template does not trigger redirect."""
        # Create a different live instance of a different template
        from world.dungeons import register_dungeon
        from typeclasses.scripts.dungeon_instance import DungeonInstanceScript

        other_template = _make_test_template(
            template_id="test_other_template",
            name="Test Other",
        )
        register_dungeon(other_template)
        other_instance = create.create_script(
            DungeonInstanceScript,
            key="test_other_template_inst",
            autostart=False,
        )
        other_instance.template_id = other_template.template_id
        other_instance.instance_key = "test_other_template_inst"
        other_instance.entrance_room_id = self.room1.id
        other_instance.start()
        try:
            self.char1.tags.add(
                other_instance.instance_key, category="dungeon_pending"
            )
            result = self.entrance._try_pending_recovery_redirect(
                self.char1, self.template
            )
            self.assertFalse(result)
            # The unrelated pending tag is preserved (not for this template)
            self.assertEqual(
                self.char1.tags.get(category="dungeon_pending"),
                other_instance.instance_key,
            )
        finally:
            try:
                other_instance.collapse_instance()
            except Exception:
                pass

    def test_active_dungeon_character_blocks_entry(self):
        """A player already inside a dungeon (dungeon_character tag set)
        cannot enter another. Pending tag is ignored in this case."""
        self.char1.tags.add(
            "some_other_instance", category="dungeon_character"
        )
        result = self.entrance.enter_dungeon(self.char1)
        self.assertFalse(result)


# ============================================================== #
#  Dungeon instance collapse — corpse keepalive, presence filtering,
#  pending-tag scrub, defensive corpse cleanup
# ============================================================== #

class TestDungeonInstanceCollapse(EvenniaTest):
    """Test collapse gate semantics and cleanup with the new corpse-recovery
    additions: corpse keepalive, physical-presence check, pending scrub."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from evennia import create_object as ev_create_object
        from world.dungeons import DUNGEON_REGISTRY, register_dungeon
        from typeclasses.scripts.dungeon_instance import DungeonInstanceScript
        from typeclasses.terrain.rooms.dungeon.dungeon_room import DungeonRoom

        DUNGEON_REGISTRY.clear()
        self.template = _make_test_template()
        register_dungeon(self.template)

        self.instance = create.create_script(
            DungeonInstanceScript,
            key="test_collapse_inst",
            autostart=False,
        )
        self.instance.template_id = self.template.template_id
        self.instance.instance_key = "test_collapse_inst"
        self.instance.entrance_room_id = self.room1.id
        self.instance.start()

        self.dungeon_room = ev_create_object(
            DungeonRoom, key="Collapse Test Room"
        )
        self.dungeon_room.tags.add(
            self.instance.instance_key, category="dungeon_room"
        )
        self.dungeon_room.dungeon_instance_id = self.instance.id
        self.instance.db.xy_grid = {(0, 0): self.dungeon_room.id}

    def tearDown(self):
        try:
            if self.instance and self.instance.pk:
                self.instance.collapse_instance()
        except Exception:
            pass
        super().tearDown()

    @patch("typeclasses.world_objects.corpse.delay")
    def test_collapse_gate_corpse_keeps_alive(self, mock_delay):
        """Instance with no characters but a tagged corpse does not collapse
        on at_repeat."""
        corpse = create_object(
            Corpse, key="corpse", location=self.dungeon_room
        )
        corpse.owner_character_key = self.char1.key
        corpse.tags.add(
            self.instance.instance_key, category="dungeon_corpse"
        )
        # No characters tagged at all; collapse gate would fire if not for corpse
        self.instance.at_repeat()
        # Instance should still be active
        self.assertEqual(self.instance.state, "active")

    def test_collapse_gate_present_character_blocks(self):
        """Character physically in a dungeon room blocks collapse."""
        self.char1.move_to(self.dungeon_room, quiet=True, move_type="teleport")
        self.char1.tags.add(
            self.instance.instance_key, category="dungeon_character"
        )
        self.instance.at_repeat()
        self.assertEqual(self.instance.state, "active")

    def test_collapse_gate_tagged_but_absent_does_not_block(self):
        """A character with a dungeon_character tag but standing in the
        world (not in a dungeon room) does not count as present and so
        does not block collapse."""
        from evennia import ScriptDB

        # Tag char1 but leave them in room1 (not a dungeon room)
        self.char1.tags.add(
            self.instance.instance_key, category="dungeon_character"
        )
        # Sanity: get_present_characters should return [] since char1 is
        # not in a dungeon room of this instance
        self.assertEqual(self.instance.get_present_characters(), [])
        instance_id = self.instance.id
        self.instance.at_repeat()
        # Instance should have collapsed and been deleted (no characters,
        # no corpses → eligible)
        self.assertFalse(ScriptDB.objects.filter(id=instance_id).exists())

    @patch("typeclasses.world_objects.corpse.delay")
    def test_collapse_scrubs_pending_tags(self, mock_delay):
        """Collapse scrubs dungeon_pending tags on absent characters."""
        self.char1.tags.add(
            self.instance.instance_key, category="dungeon_pending"
        )
        self.instance.collapse_instance()
        self.assertIsNone(self.char1.tags.get(category="dungeon_pending"))

    @patch("typeclasses.world_objects.corpse.delay")
    def test_collapse_defensive_corpse_delete(self, mock_delay):
        """Collapse with a tagged corpse despawns it as defence in depth."""
        corpse = create_object(
            Corpse, key="corpse", location=self.dungeon_room
        )
        corpse.owner_character_key = self.char1.key
        corpse.tags.add(
            self.instance.instance_key, category="dungeon_corpse"
        )
        corpse_id = corpse.id
        self.instance.collapse_instance()
        # Corpse should be deleted
        from evennia.objects.models import ObjectDB
        self.assertFalse(
            ObjectDB.objects.filter(id=corpse_id).exists()
        )

    def test_get_present_characters_filters_by_location(self):
        """get_present_characters returns only characters whose location is
        a dungeon room of this instance."""
        # char1 is tagged but NOT in a dungeon room
        self.char1.tags.add(
            self.instance.instance_key, category="dungeon_character"
        )
        # char2 tagged AND in the dungeon room
        self.char2.tags.add(
            self.instance.instance_key, category="dungeon_character"
        )
        self.char2.move_to(self.dungeon_room, quiet=True, move_type="teleport")

        present = self.instance.get_present_characters()
        self.assertIn(self.char2, present)
        self.assertNotIn(self.char1, present)
