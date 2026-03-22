"""
Tests for CmdDisarmTrap — disarm a detected trap using SUBTERFUGE skill.

evennia test --settings settings tests.command_tests.test_cmd_disarm_trap
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.class_skill_cmdsets.class_skill_cmds.cmd_disarm_trap import (
    CmdDisarmTrap,
)
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"
_CHAR = "typeclasses.actors.character.FCMCharacter"


def _give_subterfuge(char, mastery=MasteryLevel.SKILLED):
    char.db.class_skill_mastery_levels = {
        skills.SUBTERFUGE.value: {
            "mastery": mastery.value,
            "classes": ["Thief"],
        },
    }


class TestCmdDisarmTrap(EvenniaCommandTest):

    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    # ── Argument validation ──

    def test_no_args(self):
        self.call(CmdDisarmTrap(), "", "Disarm what?")

    def test_target_not_found(self):
        self.call(CmdDisarmTrap(), "unicorn", "You don't see 'unicorn' here.")

    # ── Room keyword targeting (pressure plates) ──

    def test_room_keyword_no_trap(self):
        """Room keyword when room isn't trapped."""
        self.call(CmdDisarmTrap(), "floor", "You don't see a trap here.")

    def test_room_keyword_pressure_plate(self):
        """Room keyword finds trapped room and attempts disarm."""
        plate_room = create.create_object(
            "typeclasses.terrain.rooms.room_pressure_plate.PressurePlateRoom",
            key="narrow passage",
            nohome=True,
        )
        plate_room.is_trapped = True
        plate_room.trap_armed = True
        plate_room.trap_detected = True
        plate_room.trap_disarm_dc = 5
        plate_room.trap_description = "a pressure plate"

        self.char1.move_to(plate_room, quiet=True)
        _give_subterfuge(self.char1)

        with patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
                   return_value=20):
            # at_trap_disarm sends unfreeze message first
            self.call(CmdDisarmTrap(), "floor",
                      "The pressure plate clicks harmlessly")

        self.assertFalse(plate_room.trap_armed)

    # ── Object targeting ──

    def test_disarm_trapped_object(self):
        """Disarm a trapped chest in the room."""
        chest = create.create_object(
            "typeclasses.world_objects.trap_chest.TrapChest",
            key="ornate chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_trapped = True
        chest.trap_armed = True
        chest.trap_detected = True
        chest.trap_disarm_dc = 5
        chest.trap_description = "a poison dart trap"

        _give_subterfuge(self.char1)
        with patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
                   return_value=20):
            self.call(CmdDisarmTrap(), "ornate chest", "You carefully disarm")

        self.assertFalse(chest.trap_armed)

    def test_disarm_non_trapped_object(self):
        """Trying to disarm a non-trapped object."""
        chest = create.create_object(
            "typeclasses.world_objects.trap_chest.TrapChest",
            key="plain chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_trapped = False
        self.call(CmdDisarmTrap(), "plain chest", "plain chest doesn't have a trap")

    def test_disarm_undetected_trap(self):
        """Can't disarm a trap you haven't detected."""
        chest = create.create_object(
            "typeclasses.world_objects.trap_chest.TrapChest",
            key="chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_trapped = True
        chest.trap_armed = True
        chest.trap_detected = False

        _give_subterfuge(self.char1)
        self.call(CmdDisarmTrap(), "chest", "You don't see a trap to disarm.")

    def test_disarm_already_disarmed(self):
        """Can't disarm a trap that's already disarmed."""
        chest = create.create_object(
            "typeclasses.world_objects.trap_chest.TrapChest",
            key="chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_trapped = True
        chest.trap_armed = False
        chest.trap_detected = True

        _give_subterfuge(self.char1)
        self.call(CmdDisarmTrap(), "chest", "The trap is already disarmed.")

    def test_disarm_no_skill(self):
        """Character without SUBTERFUGE can't disarm."""
        chest = create.create_object(
            "typeclasses.world_objects.trap_chest.TrapChest",
            key="chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_trapped = True
        chest.trap_armed = True
        chest.trap_detected = True

        # No subterfuge skill set
        self.call(CmdDisarmTrap(), "chest", "You don't have the skill")

    def test_disarm_failure_triggers_trap(self):
        """Failed disarm triggers the trap on the character."""
        chest = create.create_object(
            "typeclasses.world_objects.trap_chest.TrapChest",
            key="chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_trapped = True
        chest.trap_armed = True
        chest.trap_detected = True
        chest.trap_disarm_dc = 30
        chest.trap_damage_dice = "1d4"
        chest.trap_damage_type = "fire"

        self.char1.db.hp = 50
        _give_subterfuge(self.char1)

        with patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
                   return_value=1):
            with patch("utils.dice_roller.DiceRoller.roll", return_value=2):
                # trigger_trap sends damage message first
                self.call(CmdDisarmTrap(), "chest", "A trap springs!")

        self.assertLess(self.char1.db.hp, 50)

    # ── Exit targeting ──

    def test_disarm_trapped_exit(self):
        """Disarm a trapped exit (tripwire)."""
        tripwire = create.create_object(
            "typeclasses.terrain.exits.exit_tripwire.TripwireExit",
            key="north",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        tripwire.is_trapped = True
        tripwire.trap_armed = True
        tripwire.trap_detected = True
        tripwire.trap_disarm_dc = 5

        _give_subterfuge(self.char1)
        with patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
                   return_value=20):
            self.call(CmdDisarmTrap(), "north", "You carefully disarm")

        self.assertFalse(tripwire.trap_armed)
