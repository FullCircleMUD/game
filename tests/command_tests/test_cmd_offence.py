"""
Tests for the offence command (STRATEGY skill — group offensive stance).

evennia test --settings settings tests.command_tests.test_cmd_offence
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.class_skill_cmdsets.class_skill_cmds.cmd_offence import (
    CmdOffence, OFFENCE_SCALING,
)
from combat.combat_utils import enter_combat
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


class _OffenceTestBase(EvenniaCommandTest):
    """Shared setUp/tearDown for offence tests."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.char1.hp = 20
        self.char1.hp_max = 20
        self.char2.hp = 20
        self.char2.hp_max = 20

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        super().tearDown()

    def _set_mastery(self, char, level):
        if not char.db.skill_mastery_levels:
            char.db.skill_mastery_levels = {}
        char.db.skill_mastery_levels[skills.STRATEGY.value] = level.value


# ================================================================== #
#  Gate Tests
# ================================================================== #


class TestOffenceGates(_OffenceTestBase):
    """Test offence command gate checks."""

    def test_unskilled_blocked(self):
        """Unskilled characters can't set stances."""
        self._set_mastery(self.char1, MasteryLevel.UNSKILLED)
        result = self.call(CmdOffence(), "")
        self.assertIn("need training", result)

    def test_not_in_combat(self):
        """Can't set stance outside combat."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdOffence(), "")
        self.assertIn("must be in combat", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_follower_cannot_set_stance(self, mock_ticker):
        """Only the group leader can set stances."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        mob = create.create_object(
            "typeclasses.actors.mobs.dire_wolf.DireWolf",
            key="dire wolf",
            location=self.room1,
        )
        mob.hp = 30
        mob.hp_max = 30
        try:
            enter_combat(self.char1, mob)
            # char1 follows char2 → char1 is not leader
            self.char1.following = self.char2
            result = self.call(CmdOffence(), "", caller=self.char1)
            self.assertIn("Only the group leader", result)
        finally:
            self.char1.following = None
            for h in mob.scripts.get("combat_handler") or []:
                h.stop()
                h.delete()
            mob.delete()


# ================================================================== #
#  Mechanic Tests
# ================================================================== #


class TestOffenceMechanics(_OffenceTestBase):
    """Test offence stance mechanics."""

    def setUp(self):
        super().setUp()
        self.mob = create.create_object(
            "typeclasses.actors.mobs.dire_wolf.DireWolf",
            key="dire wolf",
            location=self.room1,
        )
        self.mob.hp = 30
        self.mob.hp_max = 30

    def tearDown(self):
        handlers = self.mob.scripts.get("combat_handler")
        if handlers:
            for h in handlers:
                h.stop()
                h.delete()
        self.mob.delete()
        super().tearDown()

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_offence_applies_stat_bonuses(self, mock_ticker):
        """Offence applies hit bonus and AC penalty."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        hit_before = self.char1.total_hit_bonus
        ac_before = self.char1.armor_class

        self.call(CmdOffence(), "", caller=self.char1)

        scaling = OFFENCE_SCALING[MasteryLevel.BASIC]
        self.assertEqual(self.char1.total_hit_bonus, hit_before + scaling["hit"])
        self.assertEqual(self.char1.armor_class, ac_before + scaling["ac"])

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_offence_toggle_removes(self, mock_ticker):
        """Calling offence again removes the stance."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        hit_before = self.char1.total_hit_bonus

        self.call(CmdOffence(), "", caller=self.char1)
        self.assertTrue(self.char1.has_effect("offensive_stance"))

        result = self.call(CmdOffence(), "", caller=self.char1)
        self.assertIn("normal stance", result)
        self.assertFalse(self.char1.has_effect("offensive_stance"))
        self.assertEqual(self.char1.total_hit_bonus, hit_before)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_offence_replaces_defence(self, mock_ticker):
        """Activating offence removes active defensive stance."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        # Apply defensive stance first
        from commands.class_skill_cmdsets.class_skill_cmds.cmd_defence import CmdDefence
        self.call(CmdDefence(), "", caller=self.char1)
        self.assertTrue(self.char1.has_effect("defensive_stance"))

        # Now activate offence
        self.call(CmdOffence(), "", caller=self.char1)
        self.assertFalse(self.char1.has_effect("defensive_stance"))
        self.assertTrue(self.char1.has_effect("offensive_stance"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_offence_applies_to_group(self, mock_ticker):
        """Offence applies to all group members in combat."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)

        # char2 follows char1 → char1 is leader
        self.char2.following = self.char1

        self.call(CmdOffence(), "", caller=self.char1)

        self.assertTrue(self.char1.has_effect("offensive_stance"))
        self.assertTrue(self.char2.has_effect("offensive_stance"))

        self.char2.following = None

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_grandmaster_no_ac_penalty(self, mock_ticker):
        """Grandmaster offence has no AC penalty."""
        self._set_mastery(self.char1, MasteryLevel.GRANDMASTER)
        enter_combat(self.char1, self.mob)

        ac_before = self.char1.armor_class

        self.call(CmdOffence(), "", caller=self.char1)

        self.assertEqual(self.char1.armor_class, ac_before)
        scaling = OFFENCE_SCALING[MasteryLevel.GRANDMASTER]
        self.assertEqual(scaling["ac"], 0)
