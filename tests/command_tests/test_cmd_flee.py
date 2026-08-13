"""
Tests for CmdFlee — flee from combat or comic panic run.

evennia test --settings settings tests.command_tests.test_cmd_flee
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_flee import CmdFlee


class TestCmdFleeInCombat(EvenniaCommandTest):
    """Test flee during combat."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        self.char1.hp = 20
        self.char1.hp_max = 20
        self.char2.hp = 20
        self.char2.hp_max = 20
        # Remove Evennia's default "out" exit so we control exits precisely
        if self.exit:
            self.exit.delete()
            self.exit = None
        # Create a single exit from room1 to room2
        self.exit1 = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.room2,
        )

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        if self.exit1:
            self.exit1.delete()
        super().tearDown()

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_success_moves_to_random_exit(self, mock_ticker, mock_dice):
        """Successful flee moves character to exit destination."""
        mock_dice.roll.return_value = 15
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("flee", result.lower())
        self.assertEqual(self.char1.location, self.room2)

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_success_removes_combat_handler(self, mock_ticker, mock_dice):
        """Successful flee removes the combat handler."""
        mock_dice.roll.return_value = 15
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        self.call(CmdFlee(), "", caller=self.char1)
        self.assertFalse(self.char1.scripts.get("combat_handler"))

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_fail_stays_in_room(self, mock_ticker, mock_dice):
        """Failed flee keeps character in original room."""
        mock_dice.roll.return_value = 1
        self.char1.dexterity = 8  # -1 mod, total = 0
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("can't escape", result)
        self.assertEqual(self.char1.location, self.room1)

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_fail_enemies_get_advantage(self, mock_ticker, mock_dice):
        """Failed flee gives all enemies 1 round of advantage."""
        mock_dice.roll.return_value = 1
        self.char1.dexterity = 8
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        self.call(CmdFlee(), "", caller=self.char1)

        # char2 (enemy) should have advantage against char1
        enemy_handler = self.char2.scripts.get("combat_handler")
        self.assertTrue(enemy_handler)
        self.assertTrue(enemy_handler[0].has_advantage(self.char1))
        self.assertEqual(enemy_handler[0].advantage_against[self.char1.id], 1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_no_exits(self, mock_ticker):
        """Flee with no available exits shows error."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        # Remove the exit
        self.exit1.delete()
        self.exit1 = None

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("nowhere to go", result)
        self.assertEqual(self.char1.location, self.room1)

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_combat_ends_for_remaining(self, mock_ticker, mock_dice):
        """After flee, remaining side's combat ends if no enemies left."""
        mock_dice.roll.return_value = 15
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        self.call(CmdFlee(), "", caller=self.char1)

        # char2 should also have combat ended (no enemies left in room)
        self.assertFalse(self.char2.scripts.get("combat_handler"))

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_locked_exit_filtered(self, mock_ticker, mock_dice):
        """Exits that fail traverse check are filtered out."""
        mock_dice.roll.return_value = 15
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        # Lock the only exit so traverse fails
        self.exit1.locks.add("traverse:false()")

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("nowhere to go", result)
        self.assertEqual(self.char1.location, self.room1)


class TestCmdFleeRoomMessages(EvenniaCommandTest):
    """
    Flee announces through the movement seam rather than writing its own room
    message — so both rooms hear it, and the direction is a direction.
    """

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        # These tests assert on names in room messages, so the watchers must be
        # able to see. An unlit room redacts every name to "Someone".
        self.room1.always_lit = True
        self.room2.always_lit = True
        for char in (self.char1, self.char2):
            char.hp = 20
            char.hp_max = 20
        if self.exit:
            self.exit.delete()
            self.exit = None

        # A real directional exit — its key is the destination's name, which is
        # exactly what flee used to print at players.
        self.exit1 = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="Room2",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        self.exit1.direction = "north"
        self.back = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="Room1",
            location=self.room2,
            destination=self.room1,
            nohome=True,
        )
        self.back.direction = "south"

        self.here = self._watcher("Bystander", self.room1)
        self.there = self._watcher("Watcher", self.room2)

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for handler in handlers:
                    handler.stop()
                    handler.delete()
        super().tearDown()

    def _watcher(self, key, room):
        watcher = create.create_object(
            self.character_typeclass, key=key, location=room, home=room
        )
        watcher.msg = MagicMock()
        return watcher

    def _lines(self, watcher):
        said = []
        for args, kwargs in watcher.msg.call_args_list:
            payload = kwargs.get("text", args[0] if args else None)
            if isinstance(payload, tuple):
                payload = payload[0]
            if payload:
                said.append(str(payload))
        return said

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_combat_flee_announces_a_direction_not_an_exit_name(
        self, mock_ticker, mock_dice
    ):
        mock_dice.roll.return_value = 15
        from combat.combat_utils import enter_combat

        enter_combat(self.char1, self.char2)
        self.call(CmdFlee(), "", caller=self.char1)

        self.assertIn("Char flees north!", self._lines(self.here))
        for line in self._lines(self.here):
            self.assertNotIn("Room2", line)

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_combat_flee_is_heard_on_arrival(self, mock_ticker, mock_dice):
        """The destination room used to hear nothing at all."""
        mock_dice.roll.return_value = 15
        from combat.combat_utils import enter_combat

        enter_combat(self.char1, self.char2)
        self.call(CmdFlee(), "", caller=self.char1)

        self.assertIn("Char flees in from the south!", self._lines(self.there))

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_combat_flee_announces_once(self, mock_ticker, mock_dice):
        """One line, not the command's own plus the seam's."""
        mock_dice.roll.return_value = 15
        from combat.combat_utils import enter_combat

        enter_combat(self.char1, self.char2)
        self.call(CmdFlee(), "", caller=self.char1)

        about_char = [ln for ln in self._lines(self.here) if ln.startswith("Char ")]
        self.assertEqual(about_char, ["Char flees north!"])

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_tells_the_fleeing_character_the_direction(
        self, mock_ticker, mock_dice
    ):
        mock_dice.roll.return_value = 15
        from combat.combat_utils import enter_combat

        enter_combat(self.char1, self.char2)
        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("You flee north!", result)

    def test_panic_flee_keeps_its_own_wording(self):
        self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn(
            "Char panics and flees north for no apparent reason!",
            self._lines(self.here),
        )

    def test_panic_flee_is_heard_on_arrival(self):
        self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn(
            "Char arrives from the south, in a blind panic.", self._lines(self.there)
        )


class TestCmdFleeOutOfCombat(EvenniaCommandTest):
    """Test flee when not in combat (comic panic run)."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.hp = 20
        self.char1.hp_max = 20
        # Remove Evennia's default "out" exit
        if self.exit:
            self.exit.delete()
            self.exit = None
        # Create a single exit
        self.exit1 = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="south",
            location=self.room1,
            destination=self.room2,
        )

    def tearDown(self):
        if self.exit1:
            self.exit1.delete()
        super().tearDown()

    def test_flee_not_in_combat_moves(self):
        """Out-of-combat flee moves through random exit."""
        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("panic", result)
        self.assertEqual(self.char1.location, self.room2)

    def test_flee_not_in_combat_no_exits(self):
        """Out-of-combat flee with no exits shows panic message."""
        self.exit1.delete()
        self.exit1 = None

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("nowhere to run", result)
        self.assertEqual(self.char1.location, self.room1)


class TestCmdFleeDoors(EvenniaCommandTest):
    """Door state gates flee.

    A door's closed/locked state lives on the door, not in its traverse
    lock, so an exit passing ``access(caller, "traverse")`` says nothing
    about whether it can actually be walked through.
    """

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        for char in (self.char1, self.char2):
            char.hp = 20
            char.hp_max = 20
        # Remove Evennia's default "out" exit so we control exits precisely
        if self.exit:
            self.exit.delete()
            self.exit = None
        # The only way out of room1 is a door, closed by default
        self.door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="a heavy oak door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        self.door.set_direction("north")

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        if self.door.pk:
            self.door.delete()
        super().tearDown()

    def _enter_combat(self):
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_combat_flee_blocked_by_closed_door(self, mock_ticker, mock_dice):
        """A closed door is not an escape route."""
        mock_dice.roll.return_value = 15
        self._enter_combat()

        result = self.call(CmdFlee(), "", caller=self.char1)

        self.assertEqual(self.char1.location, self.room1)
        self.assertIn("nowhere to go", result)

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_combat_flee_blocked_by_locked_door(self, mock_ticker, mock_dice):
        """A locked door is not an escape route either."""
        mock_dice.roll.return_value = 15
        self.door.is_locked = True
        self._enter_combat()

        result = self.call(CmdFlee(), "", caller=self.char1)

        self.assertEqual(self.char1.location, self.room1)
        self.assertIn("nowhere to go", result)

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_combat_flee_goes_through_an_open_door(self, mock_ticker, mock_dice):
        """An open door is a normal exit."""
        mock_dice.roll.return_value = 15
        self.door.is_open = True
        self._enter_combat()

        self.call(CmdFlee(), "", caller=self.char1)

        self.assertEqual(self.char1.location, self.room2)

    @patch("combat.combat_utils.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_combat_flee_picks_the_open_exit(self, mock_ticker, mock_dice):
        """With one closed door and one open exit, flee takes the open one."""
        mock_dice.roll.return_value = 15
        room3 = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase", key="Room3"
        )
        open_exit = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="south",
            location=self.room1,
            destination=room3,
        )
        # LIFO — the exit must go before the room it points at
        self.addCleanup(room3.delete)
        self.addCleanup(open_exit.delete)
        self._enter_combat()

        self.call(CmdFlee(), "", caller=self.char1)

        self.assertEqual(self.char1.location, room3)

    def test_panic_flee_blocked_by_closed_door(self):
        """Out-of-combat panic run respects doors too."""
        result = self.call(CmdFlee(), "", caller=self.char1)

        self.assertEqual(self.char1.location, self.room1)
        self.assertIn("nowhere to run", result)

    def test_panic_flee_goes_through_an_open_door(self):
        self.door.is_open = True

        self.call(CmdFlee(), "", caller=self.char1)

        self.assertEqual(self.char1.location, self.room2)


class TestCmdFleeBlockedByMovementEffects(EvenniaCommandTest):
    """Pre-flight guard: held actors can't flee, no broadcast, no combat exit.

    Regression coverage for the kobold-flees-while-stunned bug — AI paths
    bypassed combat_handler's gate via execute_cmd("flee"). cmd_flee now
    rejects up-front when the actor has any MOVEMENT_BLOCKING_EFFECT.
    """

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        self.char1.hp = 20
        self.char1.hp_max = 20
        self.char2.hp = 20
        self.char2.hp_max = 20
        if self.exit:
            self.exit.delete()
            self.exit = None
        self.exit1 = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key="north",
            location=self.room1,
            destination=self.room2,
        )

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        if self.exit1:
            self.exit1.delete()
        super().tearDown()

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_stunned_actor_cannot_flee(self, mock_ticker):
        """Stunned actor stays in room — the original bug."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        self.char1.apply_stunned(2)

        result = self.call(CmdFlee(), "", caller=self.char1)

        self.assertIn("try to flee", result.lower())
        self.assertIn("stunned", result.lower())
        self.assertEqual(self.char1.location, self.room1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_blocked_flee_does_not_end_combat(self, mock_ticker):
        """Pre-flight guard fires BEFORE handler.stop_combat()."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        self.char1.apply_stunned(2)

        self.call(CmdFlee(), "", caller=self.char1)

        # Combat handler must still be active on the held actor
        self.assertTrue(self.char1.scripts.get("combat_handler"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_blocked_flee_does_not_broadcast(self, mock_ticker):
        """No 'X flees north!' message reaches the room when blocked."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        self.char1.apply_stunned(2)

        # Capture broadcasts to char2 (who would see char1 flee)
        char2_msg = MagicMock()
        self.char2.msg = char2_msg

        self.call(CmdFlee(), "", caller=self.char1)

        for call_args in char2_msg.call_args_list:
            sent = call_args.args[0] if call_args.args else ""
            self.assertNotIn("flees", sent.lower())
            self.assertNotIn("flee north", sent.lower())

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_prone_blocks_flee(self, mock_ticker):
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        self.char1.apply_prone(1)

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("prone", result.lower())
        self.assertEqual(self.char1.location, self.room1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_paralysed_blocks_flee(self, mock_ticker):
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        self.char1.apply_paralysed(1)

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("paralysed", result.lower())
        self.assertEqual(self.char1.location, self.room1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_entangled_blocks_flee(self, mock_ticker):
        """Demotion regression: entangled is movement-blocking, must stop flee."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        self.char1.apply_entangled(3, save_dc=15)

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("entangled", result.lower())
        self.assertEqual(self.char1.location, self.room1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_thorn_whip_blocks_flee(self, mock_ticker):
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        self.char1.apply_named_effect(
            key="thorn_whip_held", duration=3, duration_type="combat_rounds",
            messages={"start": "...", "end": "..."},
        )

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("vines", result.lower())
        self.assertEqual(self.char1.location, self.room1)
