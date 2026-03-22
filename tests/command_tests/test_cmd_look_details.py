"""
Tests for room details — lightweight examinable descriptions via ``look``.
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_override_look import CmdLook


class TestCmdLookDetails(EvenniaCommandTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    # ------------------------------------------------------------------ #
    #  Tests
    # ------------------------------------------------------------------ #

    def test_detail_exact_match(self):
        """Looking at a detail keyword shows the description."""
        self.room1.details = {"fountain": "A moss-covered stone fountain."}
        self.call(CmdLook(), "fountain", "A moss-covered stone fountain.")

    def test_detail_case_insensitive(self):
        """Detail lookup is case-insensitive."""
        self.room1.details = {"Fountain": "A moss-covered stone fountain."}
        self.call(CmdLook(), "fountain", "A moss-covered stone fountain.")

    def test_detail_uppercase_input(self):
        """Player input in uppercase still matches."""
        self.room1.details = {"fountain": "A moss-covered stone fountain."}
        self.call(CmdLook(), "FOUNTAIN", "A moss-covered stone fountain.")

    def test_no_detail_falls_through(self):
        """Looking at a non-existent detail falls through to super()."""
        self.room1.details = {"fountain": "A moss-covered stone fountain."}
        self.call(CmdLook(), "nonexistent", "Could not find 'nonexistent'.")

    def test_empty_details_dict(self):
        """Room with empty details dict falls through normally."""
        self.room1.details = {}
        self.call(CmdLook(), "fountain", "Could not find 'fountain'.")

    def test_multiple_details(self):
        """Multiple details on a room each resolve independently."""
        self.room1.details = {
            "fountain": "A moss-covered stone fountain.",
            "statue": "A weathered marble statue.",
        }
        self.call(CmdLook(), "fountain", "A moss-covered stone fountain.")
        self.call(CmdLook(), "statue", "A weathered marble statue.")

    def test_real_object_takes_priority(self):
        """A real object in the room is found before room details."""
        from evennia.utils import create
        create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="fountain",
            location=self.room1,
            nohome=True,
        )
        self.room1.details = {"fountain": "A detail that should not show."}
        # super().func() finds the actual object and shows its description
        result = self.call(CmdLook(), "fountain", "fountain")
        self.assertNotIn("A detail that should not show.", result)
