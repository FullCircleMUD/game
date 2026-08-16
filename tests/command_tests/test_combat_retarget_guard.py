"""Tests that combat cannot wedge on an unattackable retarget candidate.

get_sides() reads the room's contents cache, which can list an object whose
location has moved on. The auto-retarget branch previously took the first
enemy unfiltered, so it would re-select the object the attack guard had
just rejected — looping every tick with no exit.
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest


class TestRetargetSkipsUnattackable(EvenniaCommandTest):
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self._created = []
        for char in (self.char1, self.char2):
            char.hp = 20
            char.hp_max = 20

    def tearDown(self):
        for char in (self.char1, self.char2):
            for handler in char.scripts.get("combat_handler") or []:
                handler.stop()
                handler.delete()
        # Delete objects this test made. Without this they outlive the test
        # and leak into later suites via the idmapper, which surfaces as
        # unrelated failures in whichever file happens to run next.
        for obj in reversed(self._created):
            if obj.pk:
                obj.delete()
        self._created = []
        super().tearDown()

    def _elsewhere(self):
        room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase", key="Elsewhere",
        )
        self._created.append(room)
        return room

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_out_of_room_enemy_is_not_retargeted(self, _ticker):
        """A phantom in the contents cache must not be chosen as the target."""
        from combat.combat_utils import enter_combat

        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]

        # char2 is a real enemy but has left the room — the exact shape of
        # the live bug, where the cache still listed a departed mob.
        self.char2.location = self._elsewhere()
        handler.action_dict = {
            "key": "attack", "target": self.char2, "dt": 4, "repeat": True,
        }

        with patch("combat.combat_utils.get_sides",
                   return_value=([], [self.char2])):
            handler.execute_next_action()

        # Combat must end rather than retarget the out-of-room enemy.
        self.assertFalse(
            self.char1.scripts.get("combat_handler"),
            "combat should have stopped, not retargeted a phantom",
        )

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_does_not_repeat_the_rejected_target(self, _ticker):
        """The wedge itself: the branch must not re-pick the failed target."""
        from combat.combat_utils import enter_combat

        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        self.char2.location = self._elsewhere()
        handler.action_dict = {
            "key": "attack", "target": self.char2, "dt": 4, "repeat": True,
        }

        messages = []
        self.char1.msg = lambda text="", **kw: messages.append(str(text))

        with patch("combat.combat_utils.get_sides",
                   return_value=([], [self.char2])):
            handler.execute_next_action()

        self.assertFalse(
            [m for m in messages if "turn to attack" in m],
            "must not announce a retarget onto the rejected target",
        )

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_valid_in_room_enemy_is_still_retargeted(self, _ticker):
        """Regression guard: normal retargeting must keep working."""
        from combat.combat_utils import enter_combat

        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]

        gone = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="Gone", location=self._elsewhere(),
        )
        self._created.append(gone)
        gone.hp = 20
        handler.action_dict = {
            "key": "attack", "target": gone, "dt": 4, "repeat": True,
        }

        # Phantom first in the list, valid enemy second — must skip to char2.
        with patch("combat.combat_utils.get_sides",
                   return_value=([], [gone, self.char2])):
            handler.execute_next_action()

        self.assertEqual(handler.action_dict.get("target"), self.char2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_dead_enemy_is_not_retargeted(self, _ticker):
        """hp<=0 candidates are rejected the same way as out-of-room ones."""
        from combat.combat_utils import enter_combat

        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        self.char2.hp = 0
        handler.action_dict = {
            "key": "attack", "target": self.char2, "dt": 4, "repeat": True,
        }

        with patch("combat.combat_utils.get_sides",
                   return_value=([], [self.char2])):
            handler.execute_next_action()

        self.assertFalse(
            self.char1.scripts.get("combat_handler"),
            "combat should have stopped on a dead-only enemy list",
        )
