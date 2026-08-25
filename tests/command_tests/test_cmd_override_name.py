"""
Tests that @name refuses to rename characters and accounts.

The XRPL mirror records ownership against a character's *name* —
``FungibleGameState.character_key`` and ``NFTGameState.character_key`` are
CharFields, not foreign keys. Renaming a character orphans every gold,
resource and NFT row it owns, with no error raised and nothing to
indicate it happened.

@name reaches characters because FCM's CharacterCmdSet merges on top of
Evennia's defaults rather than replacing them, so the whole building set
is present and gated only by permission.

evennia test --settings settings tests.command_tests.test_cmd_override_name
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_override_name import CmdName


class TestNameRefusesActors(EvenniaCommandTest):
    """Characters and accounts are off limits; objects are not."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    account_typeclass = "typeclasses.accounts.accounts.Account"
    databases = "__all__"

    def create_script(self):
        pass

    def test_renaming_a_character_is_refused(self):
        original = self.char2.key

        msg = self.call(CmdName(), f"{self.char2.key} = Renamed")

        self.assertIn("cannot be renamed", msg)
        self.char2.refresh_from_db()
        self.assertEqual(self.char2.key, original)

    def test_the_refusal_explains_why(self):
        """A builder who does not know about the mirror needs the reason."""
        msg = self.call(CmdName(), f"{self.char2.key} = Renamed")

        self.assertIn("gold, resources and items", msg)

    def test_renaming_an_account_is_refused(self):
        msg = self.call(CmdName(), "*someaccount = Renamed")

        self.assertIn("Accounts cannot be renamed", msg)

    def test_account_refusal_does_not_depend_on_finding_it(self):
        """Refused before the search, so a typo cannot change the answer."""
        msg = self.call(CmdName(), "*noSuchAccountAnywhere = Renamed")

        self.assertIn("Accounts cannot be renamed", msg)

    def test_renaming_an_ordinary_object_still_works(self):
        """Builders rename things constantly; only actors are protected."""
        self.call(CmdName(), f"{self.obj1.key} = Renamed Thing")

        self.obj1.refresh_from_db()
        self.assertEqual(self.obj1.key, "Renamed Thing")

    def test_an_offline_character_is_still_protected(self):
        """The check is by typeclass, not by whether an account is attached.

        A character with no account is exactly when a builder is most
        likely to be renaming one, and exactly when an account-based
        check would let it through.
        """
        self.char2.db_account = None
        self.char2.save(update_fields=["db_account"])
        original = self.char2.key

        msg = self.call(CmdName(), f"{self.char2.key} = Renamed")

        self.assertIn("cannot be renamed", msg)
        self.char2.refresh_from_db()
        self.assertEqual(self.char2.key, original)
