"""
Tests for the animal-speak feature: ANIMAL language gating, AnimalSpeakerMixin
vocalize() per-listener rendering, cmd_pet vocalize wiring, and the
speak_with_animals spell.

evennia test --settings settings tests.command_tests.test_animal_speak
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_pet import CmdPet
from commands.all_char_cmds.cmd_say import CmdSay
from enums.condition import Condition
from enums.named_effect import NamedEffect
from world.animals.vocalisations import (
    VOCALISATIONS,
    SPOKEN_LINES,
    get_spoken_line,
    get_vocalisation,
)


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


# ================================================================== #
#  Vocalisation table
# ================================================================== #


class TestVocalisationTable(EvenniaCommandTest):
    """Lookup precedence and fallback behaviour of the vocalisation table."""

    def create_script(self):
        pass

    def test_known_species_returns_action(self):
        """Listed species + listed hook returns an action line."""
        line = get_vocalisation("dog", "stay")
        self.assertIsNotNone(line)
        self.assertIn(line, VOCALISATIONS["dog"]["stay"])

    def test_unknown_species_falls_back_to_default(self):
        """Unknown species falls back to the _default species table."""
        line = get_vocalisation("aardvark", "stay")
        self.assertIsNotNone(line)
        self.assertIn(line, VOCALISATIONS["_default"]["stay"])

    def test_unknown_hook_returns_none(self):
        """Hook not in species or _default returns None — safe to call."""
        line = get_vocalisation("dog", "no_such_hook")
        self.assertIsNone(line)

    def test_spoken_line_lookup(self):
        """SPOKEN_LINES lookup mirrors VOCALISATIONS structure."""
        line = get_spoken_line("dog", "stay")
        self.assertIsNotNone(line)
        self.assertIn(line, SPOKEN_LINES["dog"]["stay"])


# ================================================================== #
#  AnimalSpeakerMixin.vocalize()
# ================================================================== #


class TestAnimalSpeakerMixinVocalize(EvenniaCommandTest):
    """Per-listener rendering of vocalize() based on SPEAK_WITH_ANIMALS."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.dog = create.create_object(
            "typeclasses.actors.pets.war_dog.WarDog",
            key="Rex",
            location=self.room1,
        )
        self.dog.owner_key = self.char1.key

    def tearDown(self):
        if self.dog.pk:
            self.dog.delete()
        super().tearDown()

    def _capture(self, target_char):
        """Patch has_account True on a character and capture its msg() output."""
        received = []
        target_char.msg = lambda text, **kw: received.append(text)
        original_has_account = type(target_char).has_account
        type(target_char).has_account = property(lambda self_: True)
        return received, original_has_account

    def _restore_has_account(self, target_char, original):
        type(target_char).has_account = original

    def test_non_speaker_sees_action_only(self):
        """Listener without SPEAK_WITH_ANIMALS sees the action line only."""
        received, original = self._capture(self.char2)
        try:
            self.dog.vocalize("stay")
        finally:
            self._restore_has_account(self.char2, original)

        combined = " ".join(str(m) for m in received)
        self.assertIn("Rex", combined)
        # Should not include speech framing
        self.assertNotIn("says", combined.lower())
        self.assertNotIn('"', combined)

    def test_speaker_sees_dialogue(self):
        """Listener with SPEAK_WITH_ANIMALS sees the dialogue line."""
        self.char2.add_condition(Condition.SPEAK_WITH_ANIMALS)
        received, original = self._capture(self.char2)
        try:
            self.dog.vocalize("stay")
        finally:
            self._restore_has_account(self.char2, original)
            self.char2.remove_condition(Condition.SPEAK_WITH_ANIMALS)

        combined = " ".join(str(m) for m in received)
        # A speaker sees both action AND dialogue (in quotes).
        self.assertIn('"', combined)
        # Dialogue should be one of the dog 'stay' lines.
        self.assertTrue(
            any(line in combined for line in SPOKEN_LINES["dog"]["stay"])
        )

    def test_unknown_hook_no_op(self):
        """vocalize() with no matching hook is a no-op, not an error."""
        received, original = self._capture(self.char2)
        try:
            self.dog.vocalize("no_such_hook")
        finally:
            self._restore_has_account(self.char2, original)
        self.assertEqual(received, [])

    def test_speaker_view_for_unknown_species(self):
        """An unknown species still resolves via _default fallback."""
        self.dog.species = "nobodyknows"
        self.char2.add_condition(Condition.SPEAK_WITH_ANIMALS)
        received, original = self._capture(self.char2)
        try:
            self.dog.vocalize("stay")
        finally:
            self._restore_has_account(self.char2, original)
            self.char2.remove_condition(Condition.SPEAK_WITH_ANIMALS)
        combined = " ".join(str(m) for m in received)
        self.assertIn("Rex", combined)

    def test_per_instance_override_wins(self):
        """vocalisation_overrides on the instance beat the species table."""
        self.dog.vocalisation_overrides = {"stay": ["does a unique thing."]}
        received, original = self._capture(self.char2)
        try:
            self.dog.vocalize("stay")
        finally:
            self._restore_has_account(self.char2, original)
        combined = " ".join(str(m) for m in received).lower()
        self.assertIn("does a unique thing", combined)


# ================================================================== #
#  CmdSay — animal language branch
# ================================================================== #


class TestCmdSayAnimalLanguage(EvenniaCommandTest):
    """Speaker gating + listener rendering for the ANIMAL language."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.languages = {"common"}
        self.char2.db.languages = {"common"}

    def _call_and_capture_listener(self, cmd, input_args, cmdstring=None):
        received = []
        original_msg = self.char2.msg
        self.char2.msg = lambda text, **kw: received.append(text)
        original_has_account = type(self.char2).has_account
        type(self.char2).has_account = property(lambda self_: True)

        kwargs = {}
        if cmdstring:
            kwargs["cmdstring"] = cmdstring
        caller_result = self.call(cmd, input_args, **kwargs)

        type(self.char2).has_account = original_has_account
        self.char2.msg = original_msg
        return caller_result, received

    def test_speaker_without_condition_blocked(self):
        """Without SPEAK_WITH_ANIMALS the speaker can't say/animal."""
        result = self.call(CmdSay(), "hello", cmdstring="say/animal")
        self.assertIn("don't know", result.lower())

    def test_speaker_with_condition_allowed(self):
        """SPEAK_WITH_ANIMALS lets the speaker say/animal even without the language."""
        self.char1.add_condition(Condition.SPEAK_WITH_ANIMALS)
        result = self.call(CmdSay(), "hello", cmdstring="say/animal")
        self.char1.remove_condition(Condition.SPEAK_WITH_ANIMALS)
        self.assertIn('You say in Animal: "hello"', result)

    def test_listener_without_condition_hears_noises(self):
        """Listener without SPEAK_WITH_ANIMALS hears no speech framing."""
        self.char1.add_condition(Condition.SPEAK_WITH_ANIMALS)
        _, received = self._call_and_capture_listener(
            CmdSay(), "secret message", cmdstring="say/animal"
        )
        self.char1.remove_condition(Condition.SPEAK_WITH_ANIMALS)
        combined = " ".join(str(m) for m in received)
        self.assertNotIn("secret message", combined)
        self.assertIn("animal noises", combined)
        self.assertNotIn("says", combined.lower())

    def test_listener_with_condition_hears_speech(self):
        """Listener with SPEAK_WITH_ANIMALS hears the actual content."""
        self.char1.add_condition(Condition.SPEAK_WITH_ANIMALS)
        self.char2.add_condition(Condition.SPEAK_WITH_ANIMALS)
        _, received = self._call_and_capture_listener(
            CmdSay(), "secret message", cmdstring="say/animal"
        )
        self.char1.remove_condition(Condition.SPEAK_WITH_ANIMALS)
        self.char2.remove_condition(Condition.SPEAK_WITH_ANIMALS)
        combined = " ".join(str(m) for m in received)
        self.assertIn("secret message", combined)
        self.assertIn("Animal", combined)

    def test_comprehend_languages_does_not_cover_animal(self):
        """COMPREHEND_LANGUAGES must NOT unlock animal speech understanding."""
        self.char1.add_condition(Condition.SPEAK_WITH_ANIMALS)
        self.char2.add_condition(Condition.COMPREHEND_LANGUAGES)
        _, received = self._call_and_capture_listener(
            CmdSay(), "secret message", cmdstring="say/animal"
        )
        self.char1.remove_condition(Condition.SPEAK_WITH_ANIMALS)
        self.char2.remove_condition(Condition.COMPREHEND_LANGUAGES)
        combined = " ".join(str(m) for m in received)
        self.assertNotIn("secret message", combined)
        self.assertIn("animal noises", combined)


# ================================================================== #
#  CmdPet — vocalize wiring on subcommands
# ================================================================== #


class TestCmdPetVocalizeWiring(EvenniaCommandTest):
    """Verify which pet subcommands trigger vocalize() and which don't."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.dog = create.create_object(
            "typeclasses.actors.pets.war_dog.WarDog",
            key="Rex",
            location=self.room1,
        )
        self.dog.owner_key = self.char1.key
        self.dog.start_following(self.char1)

    def tearDown(self):
        if self.dog.pk:
            handlers = self.dog.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
            self.dog.delete()
        super().tearDown()

    def _vocalize_calls(self, args, cmdstring=None):
        with patch(
            "typeclasses.actors.pets.war_dog.WarDog.vocalize",
            autospec=True,
        ) as mock_vocalize:
            kwargs = {}
            if cmdstring:
                kwargs["cmdstring"] = cmdstring
            self.call(CmdPet(), args, **kwargs)
            return [c.args[1] for c in mock_vocalize.call_args_list]

    def test_stay_triggers_vocalize(self):
        hooks = self._vocalize_calls("stay")
        self.assertIn("stay", hooks)

    def test_follow_triggers_vocalize(self):
        # Pet starts following; first stop, then issue follow.
        self.dog.stop_following()
        hooks = self._vocalize_calls("follow")
        self.assertIn("follow", hooks)

    def test_feed_triggers_vocalize(self):
        hooks = self._vocalize_calls("feed")
        self.assertIn("feed", hooks)

    def test_status_does_not_trigger_vocalize(self):
        hooks = self._vocalize_calls("status")
        self.assertNotIn("stay", hooks)
        self.assertNotIn("follow", hooks)
        self.assertNotIn("feed", hooks)


# ================================================================== #
#  Speak with Animals spell
# ================================================================== #


class TestSpeakWithAnimalsSpell(EvenniaCommandTest):
    """Spell grants SPEAK_WITH_ANIMALS condition with the right duration."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from world.spells.registry import get_spell
        self.spell = get_spell("speak_with_animals")
        self.char1.db.class_skill_mastery_levels = {"nature_magic": 1}
        self.char1.mana = 50
        self.char1.hp = 20
        self.char1.hp_max = 20

    def test_grants_condition_at_basic(self):
        """Casting at BASIC tier grants SPEAK_WITH_ANIMALS for 5 minutes."""
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.SPEAK_WITH_ANIMALS))
        self.assertTrue(
            self.char1.has_effect(NamedEffect.SPEAK_WITH_ANIMALS_BUFF.value)
        )

    def test_basic_duration_is_fifteen_minutes(self):
        """At BASIC tier the spell lasts 15 minutes (900 seconds)."""
        self.spell.cast(self.char1, self.char1)
        record = self.char1.get_named_effect(
            NamedEffect.SPEAK_WITH_ANIMALS_BUFF.value
        )
        self.assertEqual(record["duration"], 900)

    def test_grandmaster_duration_is_two_hours(self):
        """At GM tier the spell lasts 2 hours (7200 seconds)."""
        self.char1.db.class_skill_mastery_levels = {"nature_magic": 5}
        self.spell.cast(self.char1, self.char1)
        record = self.char1.get_named_effect(
            NamedEffect.SPEAK_WITH_ANIMALS_BUFF.value
        )
        self.assertEqual(record["duration"], 7200)

    def test_no_double_cast(self):
        """Recasting while active refunds mana and does not stack."""
        self.spell.cast(self.char1, self.char1)
        mana_after_first = self.char1.mana
        result = self.spell.cast(self.char1, self.char1)
        self.assertFalse(result[0])
        self.assertEqual(self.char1.mana, mana_after_first)

    def test_target_type_self(self):
        """Spell is self-targeted only."""
        self.assertEqual(self.spell.target_type, "self")


# ================================================================== #
#  Chargen filter
# ================================================================== #


class TestChargenFiltersAnimal(EvenniaCommandTest):
    """Animal language must NOT be offered as a choice in chargen."""

    def create_script(self):
        pass

    def test_animal_not_in_choosable(self):
        from server.main_menu.chargen.chargen_menu import _get_choosable_languages
        items = _get_choosable_languages(auto_languages={"common"})
        keys = {key for _, key in items}
        self.assertNotIn("animal", keys)
