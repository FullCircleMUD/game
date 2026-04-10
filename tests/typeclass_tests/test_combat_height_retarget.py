"""
Tests for mid-combat height retargeting — mobs chase targets across heights,
retarget when blocked, and flee when no targets are reachable.

evennia test --settings settings tests.typeclass_tests.test_combat_height_retarget
"""

from unittest.mock import patch, MagicMock

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.flying_mixin import FlyingMixin
from typeclasses.mixins.swimming_mixin import SwimmingMixin


class FlyingTestMob(FlyingMixin, AggressiveMob):
    """Test-only flying aggressive mob."""
    preferred_height = AttributeProperty(0)


class SwimmingTestMob(SwimmingMixin, AggressiveMob):
    """Test-only swimming aggressive mob."""
    preferred_depth = AttributeProperty(0)


class TestMidCombatHeightMatching(EvenniaTest):
    """Test that mobs chase targets across heights during combat."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.max_height = 3
        self.room1.max_depth = -3

        self.char1.hp = 50
        self.char1.hp_max = 50
        self.char1.room_vertical_position = 0

    def _create_mob(self, typeclass, key="test mob"):
        mob = create.create_object(typeclass, key=key, location=self.room1)
        mob.hp = 20
        mob.hp_max = 20
        mob.is_alive = True
        mob.room_vertical_position = 0
        return mob

    def _get_handler(self, obj):
        handlers = obj.scripts.get("combat_handler")
        return handlers[0] if handlers else None

    def _setup_combat(self, mob, target):
        """Put mob and target into combat with mob attacking target."""
        from combat.combat_utils import enter_combat
        enter_combat(mob, target)
        handler = self._get_handler(mob)
        handler.action_dict = {"key": "attack", "target": target, "repeat": True}
        return handler

    def tearDown(self):
        # Clean up combat handlers
        for obj in list(self.room1.contents):
            handlers = obj.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
            if hasattr(obj, "is_alive") and obj != self.char1 and obj != self.char2:
                obj.delete()
        super().tearDown()

    # ------------------------------------------------------------------ #
    #  Flying mob chases target upward
    # ------------------------------------------------------------------ #

    @patch("evennia.utils.utils.delay")
    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_flying_mob_chases_target_upward(self, mock_agg_delay, mock_delay):
        """Flying mob should match target's height when target ascends."""
        mob = self._create_mob(FlyingTestMob, "a crow")
        handler = self._setup_combat(mob, self.char1)

        # Target flies up
        self.char1.room_vertical_position = 2
        self.assertEqual(mob.room_vertical_position, 0)

        # Execute combat tick — mob should chase
        handler.execute_next_action()
        self.assertEqual(mob.room_vertical_position, 2)

    # ------------------------------------------------------------------ #
    #  Swimming mob chases target underwater
    # ------------------------------------------------------------------ #

    @patch("evennia.utils.utils.delay")
    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_swimming_mob_chases_target_underwater(self, mock_agg_delay, mock_delay):
        """Swimming mob should match target's depth when target dives."""
        mob = self._create_mob(SwimmingTestMob, "a shark")
        handler = self._setup_combat(mob, self.char1)

        # Target dives
        self.char1.room_vertical_position = -2
        self.assertEqual(mob.room_vertical_position, 0)

        handler.execute_next_action()
        self.assertEqual(mob.room_vertical_position, -2)

    # ------------------------------------------------------------------ #
    #  Ground mob can't match — retargets
    # ------------------------------------------------------------------ #

    @patch("evennia.utils.utils.delay")
    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_ground_mob_retargets_when_blocked(self, mock_agg_delay, mock_delay):
        """Ground mob should retarget to reachable enemy when target flies."""
        mob = self._create_mob(AggressiveMob, "a goblin")
        # char2 stays on ground as alternative target
        self.char2.hp = 50
        self.char2.hp_max = 50
        self.char2.room_vertical_position = 0

        handler = self._setup_combat(mob, self.char1)
        # Also put char2 in combat
        from combat.combat_utils import enter_combat
        enter_combat(self.char2, mob)

        # Verify char2 has a combat handler (required for get_sides)
        c2_handler = self.char2.scripts.get("combat_handler")
        self.assertTrue(c2_handler, "char2 should have a combat handler")

        # Primary target flies up
        self.char1.room_vertical_position = 2

        # Verify retarget logic directly
        from combat.height_utils import can_reach_target
        weapon = None  # mobs don't wield
        self.assertFalse(can_reach_target(mob, self.char1, weapon))
        self.assertTrue(can_reach_target(mob, self.char2, weapon))

        # Check action before executing
        action_before = handler.action_dict
        self.assertEqual(action_before.get("target"), self.char1, "Target should be char1 before tick")

        handler.execute_next_action()

        # Mob should have retargeted to char2
        self.assertEqual(mob.room_vertical_position, 0)
        # Check both ndb and action_dict
        action_after = handler.action_dict
        self.assertNotEqual(
            action_after.get("target"), self.char1,
            f"Mob should NOT still target char1 (at height 2). "
            f"ndb.combat_target={mob.ndb.combat_target}, "
            f"action_target={action_after.get('target')}"
        )

    # ------------------------------------------------------------------ #
    #  Ground mob can't match, no other targets — flees
    # ------------------------------------------------------------------ #

    @patch("evennia.utils.utils.delay")
    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_ground_mob_flees_when_all_unreachable(self, mock_agg_delay, mock_delay):
        """Ground mob should flee when no targets are reachable."""
        mob = self._create_mob(AggressiveMob, "a goblin")
        handler = self._setup_combat(mob, self.char1)

        # Only target flies up — mob can't reach anyone
        self.char1.room_vertical_position = 2

        # Mock execute_cmd to verify flee is called
        mob.execute_cmd = MagicMock()
        handler.execute_next_action()
        mob.execute_cmd.assert_called_with("flee")

    # ------------------------------------------------------------------ #
    #  Height change broadcasts message
    # ------------------------------------------------------------------ #

    @patch("evennia.utils.utils.delay")
    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_height_change_broadcasts_message(self, mock_agg_delay, mock_delay):
        """Room should receive height change message when mob chases."""
        mob = self._create_mob(FlyingTestMob, "a crow")
        handler = self._setup_combat(mob, self.char1)

        # Target flies up
        self.char1.room_vertical_position = 1

        # Capture messages
        received = []
        original_msg = self.room1.msg_contents

        def capture_msg(text, *args, **kwargs):
            received.append(text)
            return original_msg(text, *args, **kwargs)

        self.room1.msg_contents = capture_msg
        handler.execute_next_action()

        # Should have a "flies upward" message
        fly_msgs = [m for m in received if "flies upward" in str(m)]
        self.assertTrue(len(fly_msgs) > 0, f"Expected flight message, got: {received}")
