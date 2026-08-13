"""
Tests for CmdTame — tame a wild animal using ANIMAL_HANDLING mastery.

Covers the command layer: mastery gating, the tameable and mastery
requirements, the per-tamer failure cooldown, and sightlessness. Success
spawns an NFT pet, so NFTService is mocked out at that boundary.

evennia test --settings settings tests.command_tests.test_cmd_tame
"""

import time
from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from commands.class_skill_cmdsets.class_skill_cmds.cmd_tame import CmdTame
from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TameTestBase(EvenniaCommandTest):
    """A handler with a tameable wolf in front of them."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.account.attributes.add("wallet_address", WALLET_A)
        self._set_mastery(MasteryLevel.SKILLED)
        self.wolf = self._make_animal()

    def _set_mastery(self, level):
        self.char1.db.class_skill_mastery_levels = {
            skills.ANIMAL_HANDLING.value: {"mastery": level.value},
        }

    def _make_animal(self, tameable=True, tame_dc=15, required="basic"):
        wolf = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a grey wolf",
            location=self.room1,
            nohome=True,
        )
        wolf.db.tameable = tameable
        wolf.db.tame_dc = tame_dc
        wolf.db.tame_mastery_required = required
        wolf.db.tame_pet_type = "wolf_pet"
        return wolf

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False


class TestTameArguments(TameTestBase):

    def test_no_args(self):
        self.call(CmdTame(), "", "Tame what?")

    def test_an_untrained_character_cannot_tame(self):
        self.char1.db.class_skill_mastery_levels = {}
        result = self.call(CmdTame(), "wolf")
        self.assertIn("don't know how to tame", result)

    def test_something_that_cannot_be_tamed(self):
        self.wolf.db.tameable = False
        self.call(CmdTame(), "wolf", "a grey wolf cannot be tamed.")

    def test_an_animal_above_your_mastery(self):
        self.wolf.db.tame_mastery_required = "grandmaster"
        result = self.call(CmdTame(), "wolf")
        self.assertIn("mastery in", result)


class TestTameOutcome(TameTestBase):

    def test_a_failed_attempt_leaves_the_animal(self):
        self.wolf.db.tame_dc = 40
        with patch("random.randint", return_value=1):
            self.call(CmdTame(), "wolf")
        self.assertTrue(self.wolf.pk)

    def test_a_failed_attempt_sets_a_cooldown(self):
        self.wolf.db.tame_dc = 40
        with patch("random.randint", return_value=1):
            self.call(CmdTame(), "wolf")
        cooldowns = self.wolf.db.tame_cooldowns or {}
        self.assertGreater(cooldowns.get(self.char1.id, 0), time.time())

    def test_a_cooling_down_animal_refuses_a_retry(self):
        self.wolf.db.tame_cooldowns = {self.char1.id: time.time() + 300}
        result = self.call(CmdTame(), "wolf")
        self.assertIn("still wary of you", result)

    def test_a_successful_attempt_removes_the_wild_animal(self):
        self.wolf.db.tame_dc = 1
        with patch(
            "blockchain.xrpl.services.nft.NFTService.assign_item_type",
            return_value=1234,
        ), patch(
            "typeclasses.mixins.nft_pet_mirror.NFTPetMirrorMixin.spawn_pet",
            return_value=None,
        ), patch("random.randint", return_value=20):
            self.call(CmdTame(), "wolf")
        self.assertIsNone(self.wolf.pk)


class TestTameSightless(TameTestBase):
    """
    Taming is reading a creature's body language as you approach, so
    sightlessness refuses it rather than costing time.
    """

    def test_a_dark_room_refuses_the_attempt(self):
        self._darken()
        result = self.call(CmdTame(), "wolf")
        self.assertIn("too dark to make out", result.lower())

    def test_the_refusal_names_what_they_asked_for(self):
        self._darken()
        result = self.call(CmdTame(), "wolf")
        self.assertIn("'wolf'", result.lower())

    def test_the_refusal_does_not_claim_it_is_absent(self):
        self._darken()
        result = self.call(CmdTame(), "wolf")
        self.assertNotIn("don't see", result.lower())

    def test_a_blinded_handler_is_refused_the_same_way(self):
        self.char1.add_condition(Condition.BLINDED)
        result = self.call(CmdTame(), "wolf")
        self.assertIn("too dark to make out", result.lower())

    def test_nothing_is_tamed_when_refused(self):
        self._darken()
        self.wolf.db.tame_dc = 1
        with patch("random.randint", return_value=20):
            self.call(CmdTame(), "wolf")
        self.assertTrue(self.wolf.pk)

    def test_darkvision_tames_normally(self):
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        self.wolf.db.tame_dc = 1
        with patch(
            "blockchain.xrpl.services.nft.NFTService.assign_item_type",
            return_value=1234,
        ), patch(
            "typeclasses.mixins.nft_pet_mirror.NFTPetMirrorMixin.spawn_pet",
            return_value=None,
        ), patch("random.randint", return_value=20):
            self.call(CmdTame(), "wolf")
        self.assertIsNone(self.wolf.pk)
