"""
Tests for the inn service gate — who is behind the bar, and whether they
will serve you.

The rule under test is the three-way split. A bartender who cannot
*perceive* you has no idea you are there, so an order arrives as a voice
from nowhere. One who perceives but cannot *see* you knows someone came
in and asks who — that challenge is the refusal. One who can see you
pours the drink.

The point of asking the bartender rather than the customer is that it
picks up things only he knows: DETECT_INVIS lets him serve an invisible
customer, BLINDED stops him serving a plainly visible one, and an unlit
inn stops him serving anyone.

evennia test --settings settings tests.command_tests.test_cmd_inn_service
"""

from unittest.mock import patch

from django.conf import settings
from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from commands.room_specific_cmds.inn.cmd_ale import CmdAle
from commands.room_specific_cmds.inn.cmd_stew import CmdStew
from commands.room_specific_cmds.inn.service import (
    CHALLENGE_COOLDOWN_SECONDS,
    bartender_refuses,
    find_bartender,
)
from enums.condition import Condition
from enums.hunger_level import HungerLevel
from enums.thirst_level import ThirstLevel


class InnServiceTest(EvenniaCommandTest):
    """A lit inn with a bartender in it and a thirsty, hungry customer."""

    room_typeclass = "typeclasses.terrain.rooms.room_inn.RoomInn"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # A bare test room is dark — nothing here is about darkness until
        # a test says so.
        self.room1.always_lit = True

        # Vault wallet keeps stew on the static fallback path; the AMM
        # path needs deferToThread and does not run synchronously.
        self.account.attributes.add(
            "wallet_address", settings.XRPL_VAULT_ADDRESS
        )
        self.char1.db.gold = 100
        self.char1.db.resources = {}
        self.char1.hunger_level = HungerLevel.HUNGRY
        self.char1.thirst_level = ThirstLevel.THIRSTY

        self.bartender = create.create_object(
            "typeclasses.actors.npcs.bartender_npc.BartenderNPC",
            key="Rowan",
            location=self.room1,
            nohome=True,
        )

    def tearDown(self):
        if self.bartender.pk:
            self.bartender.delete()
        super().tearDown()

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False

    def _refused(self):
        """Run the gate, returning what the caller was told (or None)."""
        with patch.object(type(self.char1), "msg") as mock_msg:
            refused = bartender_refuses(self.char1)
        said = mock_msg.call_args[0][0] if mock_msg.call_args else None
        return refused, said

    def _challenge_line(self):
        """Run the gate, returning what the bartender broadcast (or None).

        ``_say_to_room`` delivers to accounts, and test objects
        have none, so the method is patched and its arguments asserted.
        """
        with patch.object(
            type(self.bartender), "_say_to_room"
        ) as mock_room:
            bartender_refuses(self.char1)
        return mock_room.call_args[0][0] if mock_room.call_args else None


class TestFindBartender(InnServiceTest):

    def test_the_bartender_is_found(self):
        self.assertEqual(find_bartender(self.room1), self.bartender)

    def test_an_empty_bar_has_nobody(self):
        self.bartender.delete()
        self.assertIsNone(find_bartender(self.room1))

    def test_other_objects_are_not_mistaken_for_staff(self):
        """EvenniaTest seeds the room with obj1/obj2 — neither serves."""
        self.bartender.delete()
        self.assertIsNone(find_bartender(self.room1))
        self.assertIn(self.obj1, self.room1.contents)

    def test_no_room_is_not_an_error(self):
        self.assertIsNone(find_bartender(None))


class TestServed(InnServiceTest):
    """The ordinary case, and the one that must not regress."""

    def test_a_visible_customer_is_served(self):
        refused, _ = self._refused()
        self.assertFalse(refused)

    def test_a_room_with_no_bartender_is_self_service(self):
        """Bobbin's Kitchen: 'Take What You Need — Pay What You Can.'"""
        self.bartender.delete()
        refused, _ = self._refused()
        self.assertFalse(refused)

    def test_a_hidden_customer_is_served_where_nobody_is_serving(self):
        """No server means nobody to hide from."""
        self.bartender.delete()
        self.char1.add_condition(Condition.HIDDEN)
        refused, _ = self._refused()
        self.assertFalse(refused)


class TestCannotPerceive(InnServiceTest):
    """Concealment excludes — he has no idea anyone is there."""

    def test_a_hidden_customer_gets_no_service(self):
        self.char1.add_condition(Condition.HIDDEN)
        refused, said = self._refused()
        self.assertTrue(refused)
        self.assertIn("where the voice is coming from", said)

    def test_an_invisible_customer_gets_no_service(self):
        self.char1.add_condition(Condition.INVISIBLE)
        refused, said = self._refused()
        self.assertTrue(refused)
        self.assertIn("where the voice is coming from", said)

    def test_detect_invis_serves_an_invisible_customer(self):
        """The whole reason for asking the bartender rather than the caller.

        The old hand-rolled check read the customer's own conditions, so
        this case was impossible to express.
        """
        self.char1.add_condition(Condition.INVISIBLE)
        self.bartender.add_condition(Condition.DETECT_INVIS)
        refused, _ = self._refused()
        self.assertFalse(refused)

    def test_the_refusal_does_not_name_the_customer(self):
        """He does not know who ordered — that is the point of it."""
        self.char1.add_condition(Condition.INVISIBLE)
        _, said = self._refused()
        self.assertNotIn(self.char1.key, said)


class TestCanPerceiveButNotSee(InnServiceTest):
    """Darkness redacts — he knows someone came in and asks who."""

    def test_a_blinded_bartender_challenges(self):
        self.bartender.add_condition(Condition.BLINDED)
        refused, _ = self._refused()
        self.assertTrue(refused)

    def test_a_dark_inn_challenges(self):
        self._darken()
        refused, _ = self._refused()
        self.assertTrue(refused)

    def test_the_challenge_asks_who_is_there(self):
        self.bartender.add_condition(Condition.BLINDED)
        line = self._challenge_line()
        self.assertIsNotNone(line)
        self.assertTrue(
            any(c in line for c in self.bartender._BLIND_CHALLENGES)
        )

    def test_the_challenge_does_not_name_the_customer(self):
        self.bartender.add_condition(Condition.BLINDED)
        line = self._challenge_line()
        self.assertNotIn(self.char1.key, line)

    def test_darkvision_serves_in_the_dark(self):
        self._darken()
        self.bartender.add_condition(Condition.DARKVISION)
        refused, _ = self._refused()
        self.assertFalse(refused)

    def test_a_visible_customer_is_not_challenged(self):
        self.assertIsNone(self._challenge_line())


class TestChallengeCooldown(InnServiceTest):
    """A command fires as fast as a player types; the arrival hook does not."""

    def setUp(self):
        super().setUp()
        self.bartender.add_condition(Condition.BLINDED)

    def test_the_first_order_challenges(self):
        self.assertIsNotNone(self._challenge_line())

    def test_a_second_order_does_not_broadcast_again(self):
        self._challenge_line()
        self.assertIsNone(self._challenge_line())

    def test_a_suppressed_challenge_still_refuses(self):
        self._challenge_line()
        refused, _ = self._refused()
        self.assertTrue(refused)

    def test_a_suppressed_challenge_tells_the_caller_something(self):
        self._challenge_line()
        _, said = self._refused()
        self.assertIn("does not seem to have heard you", said)

    def test_the_caller_does_not_learn_a_name_they_cannot_see(self):
        """Blinded bartender, dark room — the customer cannot see him either."""
        self._darken()
        self._challenge_line()
        _, said = self._refused()
        self.assertNotIn(self.bartender.key, said)

    def test_the_cooldown_expires(self):
        self._challenge_line()
        self.bartender.db.last_blind_challenge_at -= (
            CHALLENGE_COOLDOWN_SECONDS + 1
        )
        self.assertIsNotNone(self._challenge_line())


class TestTheCommands(InnServiceTest):
    """The gate is wired into both commands, ahead of any other check."""

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_ale_serves_a_visible_customer(self, mock_sink):
        result = self.call(CmdAle(), "")
        self.assertIn("frothy mug of ale", result)

    def test_ale_refuses_a_hidden_customer(self):
        self.char1.add_condition(Condition.HIDDEN)
        result = self.call(CmdAle(), "")
        self.assertIn("where the voice is coming from", result)

    def test_ale_takes_no_gold_when_refused(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.call(CmdAle(), "")
        self.assertEqual(self.char1.get_gold(), 100)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_stew_serves_a_visible_customer(self, mock_sink):
        result = self.call(CmdStew(), "")
        self.assertIn("warm bowl of stew", result)

    def test_stew_refuses_a_hidden_customer(self):
        self.char1.add_condition(Condition.HIDDEN)
        result = self.call(CmdStew(), "")
        self.assertIn("where the voice is coming from", result)

    def test_stew_leaves_hunger_alone_when_refused(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.call(CmdStew(), "")
        self.assertEqual(self.char1.hunger_level, HungerLevel.HUNGRY)

    def test_the_gate_runs_before_the_not_thirsty_check(self):
        """A concealed customer is refused service, not told they are fine."""
        self.char1.thirst_level = ThirstLevel.REFRESHED
        self.char1.add_condition(Condition.HIDDEN)
        result = self.call(CmdAle(), "")
        self.assertIn("where the voice is coming from", result)
        self.assertNotIn("not thirsty", result)
