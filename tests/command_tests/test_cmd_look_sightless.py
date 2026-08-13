"""
Tests for looking while sightless — dark room or BLINDED, one rule.

Three different answers, depending on what is being looked at:

- **The room** — no gating here at all. Bare ``look`` calls the room's
  ``return_appearance``, which thins the display itself: names redact,
  the description and exits drop, but who and what is present still
  reports. That behaviour is covered by ``test_room_display``.
- **A specific actor or object** — resolved on ``p_can_perceive``, so
  presence survives, then rendered as "Someone is there, but it's too
  dark to make out any detail."
- **A direction or a room detail** — neither is a thing whose presence
  can be sensed, so both give the same answer as a blank wall.

evennia test --settings settings tests.command_tests.test_cmd_look_sightless
"""

from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_override_look import CmdLook
from enums.condition import Condition


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class LookSightlessBase(EvenniaCommandTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.account.attributes.add("wallet_address", WALLET_A)
        self.rock = create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="a mossy rock",
            location=self.room1,
            nohome=True,
        )
        self.rock.db.desc = "Green and damp."

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False


class TestLookingAtAnObject(LookSightlessBase):

    def test_the_object_is_still_sensed(self):
        self._darken()
        result = self.call(CmdLook(), "rock")
        self.assertIn("is there, but it's too dark", result)

    def test_the_description_is_withheld(self):
        self._darken()
        result = self.call(CmdLook(), "rock")
        self.assertNotIn("Green and damp", result)

    def test_the_name_is_withheld(self):
        self._darken()
        result = self.call(CmdLook(), "rock")
        self.assertNotIn("mossy", result)

    def test_it_reads_as_something(self):
        self._darken()
        result = self.call(CmdLook(), "rock")
        self.assertIn("Something is there", result)

    def test_a_custom_unseen_name_is_used(self):
        self._darken()
        self.rock.unseen_name = "a looming shape"
        result = self.call(CmdLook(), "rock")
        self.assertIn("A looming shape is there", result)

    def test_a_blinded_looker_gets_the_same(self):
        self.char1.add_condition(Condition.BLINDED)
        result = self.call(CmdLook(), "rock")
        self.assertIn("is there, but it's too dark", result)

    def test_darkvision_sees_normally(self):
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        result = self.call(CmdLook(), "rock")
        self.assertIn("Green and damp", result)

    def test_a_sighted_looker_is_unaffected(self):
        result = self.call(CmdLook(), "rock")
        self.assertIn("Green and damp", result)


class TestLookingAtSomethingCarried(LookSightlessBase):
    """
    Your own pack is no exception — a description is read, not felt.
    """

    def setUp(self):
        super().setUp()
        self.coin = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="a gold coin",
            location=self.char1,
        )
        self.coin.db.desc = "Stamped with a crown."

    def test_a_carried_item_is_still_sensed(self):
        self._darken()
        result = self.call(CmdLook(), "coin")
        self.assertIn("is there, but it's too dark", result)

    def test_a_carried_items_description_is_withheld(self):
        self._darken()
        result = self.call(CmdLook(), "coin")
        self.assertNotIn("Stamped with a crown", result)


class TestLookingAtAnActor(LookSightlessBase):

    def setUp(self):
        super().setUp()
        self.char2.location = self.room1

    def test_the_actor_is_still_sensed(self):
        self._darken()
        result = self.call(CmdLook(), "Char2")
        self.assertIn("is there, but it's too dark", result)

    def test_it_reads_as_someone(self):
        self._darken()
        result = self.call(CmdLook(), "Char2")
        self.assertIn("Someone is there", result)

    def test_the_actors_name_is_withheld(self):
        self._darken()
        result = self.call(CmdLook(), "Char2")
        self.assertNotIn(self.char2.key, result)


class TestLookingAtConcealment(LookSightlessBase):
    """
    Concealment excludes, darkness redacts. An invisible thing is absent
    whether the lights are on or not — it never reaches the sensed line.
    """

    def setUp(self):
        super().setUp()
        self.char2.location = self.room1

    def test_an_invisible_actor_is_absent_in_the_dark(self):
        self._darken()
        self.char2.add_condition(Condition.INVISIBLE)
        result = self.call(CmdLook(), "Char2")
        self.assertNotIn("is there, but it's too dark", result)

    def test_a_hidden_actor_is_absent_in_the_dark(self):
        self._darken()
        self.char2.add_condition(Condition.HIDDEN)
        result = self.call(CmdLook(), "Char2")
        self.assertNotIn("is there, but it's too dark", result)


class TestLookingAtADirection(LookSightlessBase):
    """
    A direction is not a thing you can sense, so the answer matches a
    blank wall — which is also what an absent exit gives, so it reveals
    nothing about whether a door is there.
    """

    def setUp(self):
        super().setUp()
        self.north_room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="North Room",
            nohome=True,
        )
        exit_north = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.north_room,
            nohome=True,
        )
        exit_north.set_direction("north")
        exit_north.db.desc = "A shadowed archway."

    def test_a_direction_gives_nothing_special(self):
        self._darken()
        result = self.call(CmdLook(), "north")
        self.assertIn("nothing special in that direction", result)

    def test_the_exit_description_is_withheld(self):
        self._darken()
        result = self.call(CmdLook(), "north")
        self.assertNotIn("shadowed archway", result)

    def test_a_sighted_looker_sees_the_exit(self):
        result = self.call(CmdLook(), "north")
        self.assertIn("shadowed archway", result)


class TestLookingAtADetail(LookSightlessBase):
    """
    A room detail is nothing but a description, so there is no reduced
    version of it to give.
    """

    def setUp(self):
        super().setUp()
        self.room1.db.details = {"fresco": "Faded figures dance across it."}

    def test_a_detail_is_withheld(self):
        self._darken()
        result = self.call(CmdLook(), "fresco")
        self.assertNotIn("Faded figures", result)

    def test_the_refusal_says_it_is_the_dark(self):
        self._darken()
        result = self.call(CmdLook(), "fresco")
        self.assertIn("too dark to make out any detail", result)

    def test_a_sighted_looker_reads_the_detail(self):
        result = self.call(CmdLook(), "fresco")
        self.assertIn("Faded figures", result)


class TestLookingInAContainer(LookSightlessBase):
    """
    A container can be sensed, but its contents cannot be read off.
    """

    def setUp(self):
        super().setUp()
        self.chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="iron chest",
            location=self.room1,
            nohome=True,
        )
        self.chest.is_locked = False
        self.chest.is_open = True

    def test_the_container_is_still_sensed(self):
        self._darken()
        result = self.call(CmdLook(), "in chest")
        self.assertIn("is there, but it's too dark", result)

    def test_the_contents_are_withheld(self):
        self._darken()
        create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="a silver ring",
            location=self.chest,
        )
        result = self.call(CmdLook(), "in chest")
        self.assertNotIn("silver ring", result)

    def test_a_sighted_looker_reads_the_contents(self):
        create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="a silver ring",
            location=self.chest,
        )
        result = self.call(CmdLook(), "in chest")
        self.assertIn("silver ring", result)


class TestLookingAtTheRoom(LookSightlessBase):
    """
    The room is not gated here — return_appearance thins it itself. These
    lock in that the command does not add a refusal on top.
    """

    def test_a_bare_look_still_works_in_the_dark(self):
        self._darken()
        result = self.call(CmdLook(), "")
        self.assertNotIn("too dark to make out", result)

    def test_look_around_still_works_in_the_dark(self):
        self._darken()
        result = self.call(CmdLook(), "around")
        self.assertNotIn("too dark to make out", result)

    def test_the_room_still_reports_what_is_present(self):
        """The premise the whole perceive/see split exists to serve."""
        self._darken()
        result = self.call(CmdLook(), "")
        self.assertIn("on the ground", result)
        self.assertIn("is in the room", result)
