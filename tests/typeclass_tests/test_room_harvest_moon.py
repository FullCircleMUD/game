"""
Tests for the Harvest Moon Inn room typeclass.

Covers behavior unique to RoomHarvestMoon (the Millholm inn run by
Rowan), as distinct from the generic RoomInn parent. Currently that
means the rat-cellar defeat heal Rowan performs on a player who
arrives at 1 HP with the quest still active.

evennia test --settings settings tests.typeclass_tests.test_room_harvest_moon
"""

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest


class TestHarvestMoonHealOnDefeat(EvenniaCommandTest):
    """Rowan heals a defeated rat-cellar quester on arrival."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.inn = create_object(
            "typeclasses.terrain.rooms.room_harvest_moon.RoomHarvestMoon",
            key="Test Harvest Moon",
        )

    def tearDown(self):
        if self.inn and self.inn.pk:
            self.inn.delete()
        super().tearDown()

    def test_heal_on_defeat_arrival(self):
        """Player with active rat quest and HP=1 gets healed at inn."""
        from world.quests.rat_cellar import RatCellarQuest

        self.char1.quests.add(RatCellarQuest)
        self.char1.hp = 1

        self.char1.move_to(self.inn, quiet=True)

        self.assertEqual(self.char1.hp, self.char1.effective_hp_max)

    def test_no_heal_when_quest_complete(self):
        """Player with completed quest should NOT get healed."""
        from world.quests.rat_cellar import RatCellarQuest

        quest = self.char1.quests.add(RatCellarQuest)
        quest.status = "completed"  # avoid blockchain gold reward
        self.char1.hp = 1

        self.char1.move_to(self.inn, quiet=True)

        self.assertEqual(self.char1.hp, 1)

    def test_no_heal_when_full_hp(self):
        """Player with full HP should NOT trigger the heal."""
        from world.quests.rat_cellar import RatCellarQuest

        self.char1.quests.add(RatCellarQuest)
        original_hp = self.char1.hp

        self.char1.move_to(self.inn, quiet=True)

        self.assertEqual(self.char1.hp, original_hp)
