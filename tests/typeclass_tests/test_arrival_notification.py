"""
Tests for the arrival notification — who gets told when something enters.

The bug this closes: an invisible player walked into a room and every mob
in it was handed them, so an aggressive mob attacked someone it had no
way of knowing was there. The pull side (a mob looking around) had been
fixed; the push side had not, so the same mob answered differently
depending on how it learned you had arrived.

Concealment excludes, darkness does not. A hidden or invisible arrival is
not announced at all; someone walking into an unlit room still makes
noise, and what the mob can work out from that is its own problem.

evennia test --settings settings tests.typeclass_tests.test_arrival_notification
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition


class ArrivalNotificationTest(EvenniaTest):
    """A mob standing in a room, and a character walking into it."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.room2.always_lit = True
        self.mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a sewer rat",
            location=self.room1,
            nohome=True,
        )
        # The arriving character starts elsewhere.
        self.char1.location = self.room2

    def tearDown(self):
        if self.mob.pk:
            self.mob.delete()
        super().tearDown()

    def _arrive(self):
        """Walk char1 into the mob's room, returning the notify mock."""
        with patch.object(type(self.mob), "at_new_arrival") as mock_notify:
            self.char1.location = self.room1
            self.room1.at_object_receive(self.char1, self.room2)
        return mock_notify


class TestWhoIsAnnounced(ArrivalNotificationTest):

    def test_a_visible_arrival_is_announced(self):
        self.assertTrue(self._arrive().called)

    def test_the_arriver_is_passed_to_the_mob(self):
        mock_notify = self._arrive()
        self.assertEqual(mock_notify.call_args[0][0], self.char1)

    def test_an_invisible_arrival_is_not_announced(self):
        """The wolf bug."""
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertFalse(self._arrive().called)

    def test_a_hidden_arrival_is_not_announced(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.assertFalse(self._arrive().called)

    def test_a_mob_is_not_told_about_itself(self):
        with patch.object(type(self.mob), "at_new_arrival") as mock_notify:
            self.room1.at_object_receive(self.mob, self.room2)
        self.assertFalse(mock_notify.called)


class TestTheCounters(ArrivalNotificationTest):
    """
    The counters live in the predicate, not the call site, so the push
    surface gets them for free.
    """

    def test_detect_invis_restores_an_invisible_arrival(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.mob.add_condition(Condition.DETECT_INVIS)
        self.assertTrue(self._arrive().called)

    def test_true_sight_restores_a_hidden_arrival(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.mob.apply_true_sight(duration_seconds=300)
        self.assertTrue(self._arrive().called)

    def test_true_sight_does_not_restore_an_invisible_arrival(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.mob.apply_true_sight(duration_seconds=300)
        self.assertFalse(self._arrive().called)

    def test_detect_invis_does_not_restore_a_hidden_arrival(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.mob.add_condition(Condition.DETECT_INVIS)
        self.assertFalse(self._arrive().called)


class TestDarknessDoesNotSilenceIt(ArrivalNotificationTest):
    """
    Someone walking in makes noise. Darkness costs the mob knowledge
    about the arrival, not the arrival itself.
    """

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False

    def test_a_dark_room_still_announces_the_arrival(self):
        self._darken()
        self.assertTrue(self._arrive().called)

    def test_a_blinded_mob_is_still_told(self):
        self.mob.add_condition(Condition.BLINDED)
        self.assertTrue(self._arrive().called)

    def test_concealment_still_wins_in_the_dark(self):
        """Excluded is excluded — darkness does not make it louder."""
        self._darken()
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertFalse(self._arrive().called)


class TestTheAggressiveMob(ArrivalNotificationTest):
    """
    The bug end to end: an aggressive mob must not schedule an attack on
    someone it was never told about.
    """

    def setUp(self):
        super().setUp()
        self.mob.delete()
        self.mob = create.create_object(
            "typeclasses.actors.mobs.aggressive_mob.AggressiveMob",
            key="a grey wolf",
            location=self.room1,
            nohome=True,
        )
        self.mob.is_alive = True

    def _walk_in(self):
        with patch.object(
            type(self.mob), "_try_reach_and_attack"
        ) as mock_attack:
            self.char1.location = self.room1
            self.room1.at_object_receive(self.char1, self.room2)
        return mock_attack

    def test_a_visible_player_is_attacked(self):
        self.assertTrue(self._walk_in().called)

    def test_an_invisible_player_is_not_attacked(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertFalse(self._walk_in().called)

    def test_a_hidden_player_is_not_attacked(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.assertFalse(self._walk_in().called)

    def test_a_see_invis_mob_still_attacks(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.mob.add_condition(Condition.DETECT_INVIS)
        self.assertTrue(self._walk_in().called)


class LLMArrivalTest(EvenniaTest):
    """The same dispatcher, the other hook.

    ``at_llm_player_arrive`` used to be fired from a second loop in
    ``FCMCharacter.at_post_move`` with no perception gate at all, so an
    invisible player was greeted by name. It now rides the room
    dispatcher alongside ``at_new_arrival``, behind the same predicate.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.room2.always_lit = True
        self.npc = create.create_object(
            "typeclasses.actors.npcs.llm_roleplay_npc.LLMRoleplayNPC",
            key="Rowan",
            location=self.room1,
            nohome=True,
        )
        self.npc.llm_hook_arrive = True
        self.char1.location = self.room2

    def tearDown(self):
        if self.npc.pk:
            self.npc.delete()
        super().tearDown()

    # None is a meaningful source_location (chargen), so the default
    # cannot be None — it has to be something no caller would pass.
    _UNSET = object()

    def _arrive(self, source=_UNSET, mover=None):
        """Walk something into the NPC's room, returning the hook mock."""
        mover = mover or self.char1
        source = self.room2 if source is self._UNSET else source
        with patch.object(
            type(self.npc), "at_llm_player_arrive"
        ) as mock_hook:
            mover.location = self.room1
            self.room1.at_object_receive(mover, source)
        return mock_hook


class TestTheLLMHookIsGated(LLMArrivalTest):

    def test_a_visible_arrival_reaches_the_npc(self):
        self.assertTrue(self._arrive().called)

    def test_the_arriver_is_passed_through(self):
        self.assertEqual(self._arrive().call_args[0][0], self.char1)

    def test_an_invisible_arrival_does_not(self):
        """The leak: greeted by name by someone who cannot see them."""
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertFalse(self._arrive().called)

    def test_a_hidden_arrival_does_not(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.assertFalse(self._arrive().called)

    def test_detect_invis_restores_it(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.npc.add_condition(Condition.DETECT_INVIS)
        self.assertTrue(self._arrive().called)

    def test_a_dark_room_still_reaches_the_npc(self):
        """Perceive, not see — the hook decides what to do about the dark."""
        self.room1.always_lit = False
        self.room1.natural_light = False
        self.assertTrue(self._arrive().called)

    def test_a_blinded_npc_is_still_told(self):
        self.npc.add_condition(Condition.BLINDED)
        self.assertTrue(self._arrive().called)


class TestTheExtraConditions(LLMArrivalTest):
    """Two gates the mob hook does not carry."""

    def test_chargen_placement_fires_nothing(self):
        """No source_location means being created, not arriving.

        A reactive NPC in the start room would otherwise make a blocking
        multi-second LLM call during chargen finalisation.
        """
        self.assertFalse(self._arrive(source=None).called)

    def test_a_dropped_object_is_not_greeted(self):
        """The dispatcher fires for anything entering; this hook should not."""
        self.assertFalse(self._arrive(mover=self.obj1).called)

    def test_a_mob_walking_in_is_not_greeted(self):
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a sewer rat",
            location=self.room2,
            nohome=True,
        )
        self.assertFalse(self._arrive(mover=mob).called)


class TestBlindNPCStillChallenges(LLMArrivalTest):
    """
    The sight half belongs to the hook, not the dispatcher. Gate the
    dispatcher on sight and the NPC goes silent instead of asking who is
    there — a decision the dispatcher has no business making.
    """

    def _walk_in(self):
        with patch.object(
            type(self.npc), "_deliver_blind_challenge"
        ) as mock_challenge:
            self.char1.location = self.room1
            self.room1.at_object_receive(self.char1, self.room2)
        return mock_challenge

    def test_a_blinded_npc_challenges(self):
        self.npc.add_condition(Condition.BLINDED)
        self.assertTrue(self._walk_in().called)

    def test_a_dark_room_challenges(self):
        self.room1.always_lit = False
        self.room1.natural_light = False
        self.assertTrue(self._walk_in().called)

    def test_darkvision_does_not_challenge(self):
        self.room1.always_lit = False
        self.room1.natural_light = False
        self.npc.add_condition(Condition.DARKVISION)
        self.assertFalse(self._walk_in().called)

    def test_a_concealed_arrival_is_not_even_challenged(self):
        """Nothing to challenge — he was never told anyone came in."""
        self.npc.add_condition(Condition.BLINDED)
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertFalse(self._walk_in().called)
