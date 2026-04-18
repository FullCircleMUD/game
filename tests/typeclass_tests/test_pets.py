"""
Tests for the pet system — BasePet, NFTPetMirrorMixin, CmdPet,
stable commands, combat companions, mounts.

evennia test --settings settings tests.typeclass_tests.test_pets
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_pet import CmdPet


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _make_mule(room, owner):
    """Create a mule pet in a room, owned by a character."""
    mule = create.create_object(
        "typeclasses.actors.pets.mule.Mule",
        key="a mule",
        location=room,
    )
    mule.owner_key = owner.key
    mule.start_following(owner)
    return mule


def _make_war_dog(room, owner):
    """Create a war dog pet in a room, owned by a character."""
    dog = create.create_object(
        "typeclasses.actors.pets.war_dog.WarDog",
        key="a war dog",
        location=room,
    )
    dog.owner_key = owner.key
    dog.start_following(owner)
    return dog


def _make_horse(room, owner):
    """Create a horse pet in a room, owned by a character."""
    horse = create.create_object(
        "typeclasses.actors.pets.horse.Horse",
        key="a horse",
        location=room,
    )
    horse.owner_key = owner.key
    horse.start_following(owner)
    return horse


class _PetTestBase(EvenniaCommandTest):
    """Shared setUp/tearDown for pet tests."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.allow_combat = True
        self.char1.hp = 20
        self.char1.hp_max = 20

    def tearDown(self):
        # Clean up any pets
        for obj in list(self.room1.contents):
            if getattr(obj, "is_pet", False):
                handlers = obj.scripts.get("combat_handler")
                if handlers:
                    for h in handlers:
                        h.stop()
                        h.delete()
                obj.delete()
        # Clean up combat handlers on characters
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        super().tearDown()


# ── BasePet Core ─────────────────────────────────────────────────────

class TestBasePet(_PetTestBase):
    """Test BasePet creation, following, hunger, death."""

    def test_pet_creation(self):
        """Pet should be created with correct attributes."""
        mule = _make_mule(self.room1, self.char1)
        self.assertTrue(mule.is_pet)
        self.assertEqual(mule.owner_key, self.char1.key)
        self.assertEqual(mule.pet_state, "following")
        self.assertEqual(mule.following, self.char1)

    def test_pet_stop_following(self):
        """Pet should stop following and wait."""
        mule = _make_mule(self.room1, self.char1)
        mule.stop_following()
        self.assertEqual(mule.pet_state, "waiting")
        self.assertIsNone(mule.following)

    def test_pet_hunger_fed(self):
        """Newly created pet should be fed."""
        mule = _make_mule(self.room1, self.char1)
        self.assertEqual(mule.check_hunger(), "fed")

    def test_pet_hunger_display(self):
        """Hunger display should show coloured text."""
        mule = _make_mule(self.room1, self.char1)
        self.assertIn("Fed", mule.get_hunger_display())

    def test_pet_feed_resets_hunger(self):
        """Feeding should reset the hunger timer."""
        mule = _make_mule(self.room1, self.char1)
        mule.fed_until = 0  # force expired
        self.assertNotEqual(mule.check_hunger(), "fed")
        mule.feed()
        self.assertEqual(mule.check_hunger(), "fed")

    def test_pet_room_description_following(self):
        """Following pet should show room description."""
        mule = _make_mule(self.room1, self.char1)
        desc = mule.get_room_description()
        self.assertIn("mule", desc.lower())

    def test_pet_room_description_waiting(self):
        """Waiting pet should show waiting message."""
        mule = _make_mule(self.room1, self.char1)
        mule.stop_following()
        desc = mule.get_room_description()
        self.assertIn("waits", desc.lower())

    def test_pet_die(self):
        """Pet death should delete the object."""
        mule = _make_mule(self.room1, self.char1)
        mule_id = mule.id
        mule.die(cause="test")
        # Pet should be deleted
        from evennia.objects.models import ObjectDB
        self.assertFalse(ObjectDB.objects.filter(id=mule_id).exists())


# ── CmdPet ───────────────────────────────────────────────────────────

class TestCmdPet(_PetTestBase):
    """Test pet command routing."""

    def test_pet_no_pet(self):
        """Should show error when no pet in room."""
        result = self.call(CmdPet(), "")
        self.assertIn("don't have a pet", result)

    def test_pet_status(self):
        """Should show pet status."""
        _make_mule(self.room1, self.char1)
        result = self.call(CmdPet(), "")
        self.assertIn("mule", result.lower())
        self.assertIn("Fed", result)

    def test_pet_stay(self):
        """pet stay should stop following."""
        mule = _make_mule(self.room1, self.char1)
        self.call(CmdPet(), "stay")
        self.assertEqual(mule.pet_state, "waiting")

    def test_pet_follow(self):
        """pet follow should resume following."""
        mule = _make_mule(self.room1, self.char1)
        mule.stop_following()
        self.call(CmdPet(), "follow")
        self.assertEqual(mule.pet_state, "following")

    def test_pet_feed(self):
        """pet feed should reset hunger."""
        mule = _make_mule(self.room1, self.char1)
        mule.fed_until = 0
        self.call(CmdPet(), "feed")
        self.assertEqual(mule.check_hunger(), "fed")

    def test_pet_name(self):
        """pet name should rename the pet."""
        mule = _make_mule(self.room1, self.char1)
        self.call(CmdPet(), "name Bessie")
        self.assertEqual(mule.key, "Bessie")

    def test_pet_attack_non_combat(self):
        """Mule (non-combat) should refuse to attack."""
        _make_mule(self.room1, self.char1)
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test_mob", location=self.room1,
        )
        mob.hp = 10
        mob.hp_max = 10
        result = self.call(CmdPet(), "attack test_mob")
        self.assertIn("doesn't know how to fight", result)
        mob.delete()


# ── Combat Companion ─────────────────────────────────────────────────

class TestCombatCompanion(_PetTestBase):
    """Test combat pets."""

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_pet_attack_command(self, mock_ticker):
        """pet attack should initiate combat for combat pets."""
        dog = _make_war_dog(self.room1, self.char1)
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test_mob", location=self.room1,
        )
        mob.hp = 10
        mob.hp_max = 10
        try:
            result = self.call(CmdPet(), "attack test_mob")
            self.assertIn("attack", result.lower())
        finally:
            for obj in (dog, mob):
                handlers = obj.scripts.get("combat_handler")
                if handlers:
                    for h in handlers:
                        h.stop()
                        h.delete()
            mob.delete()


# ── Mount ────────────────────────────────────────────────────────────

class TestMount(_PetTestBase):
    """Test mount functionality."""

    def test_mount_command(self):
        """pet mount should mount the horse."""
        horse = _make_horse(self.room1, self.char1)
        self.call(CmdPet(), "mount")
        self.assertTrue(horse.is_mounted)
        self.assertEqual(horse.mounted_by, self.char1.key)
        self.assertIsNotNone(self.char1.db.mounted_on)

    def test_dismount_command(self):
        """pet dismount should dismount."""
        horse = _make_horse(self.room1, self.char1)
        horse.mount(self.char1)
        self.call(CmdPet(), "dismount")
        self.assertFalse(horse.is_mounted)
        self.assertIsNone(self.char1.db.mounted_on)

    def test_mounted_room_description(self):
        """Mounted rider should show combined room description."""
        horse = _make_horse(self.room1, self.char1)
        horse.mount(self.char1)
        desc = self.char1.get_room_description()
        self.assertIn("rides", desc)
        self.assertIn("horse", desc.lower())

    def test_mounted_pet_hidden_from_room(self):
        """Mounted pet should not show separately in room."""
        horse = _make_horse(self.room1, self.char1)
        horse.mount(self.char1)
        desc = horse.get_room_description()
        self.assertEqual(desc, "")

    def test_mounted_movement_deducts_from_mount(self):
        """Moving while mounted should deduct from mount's move, not rider's."""
        horse = _make_horse(self.room1, self.char1)
        horse.mount(self.char1)
        char_move_before = self.char1.move
        horse_move_before = horse.move
        self.char1.move_to(
            self.room2, quiet=True, move_type="move", exit_obj=self.exit,
        )
        self.assertEqual(self.char1.move, char_move_before)
        self.assertEqual(horse.move, horse_move_before - 1)

    def test_unmounted_movement_deducts_from_character(self):
        """Moving without a mount should deduct from character's move."""
        char_move_before = self.char1.move
        self.char1.move_to(
            self.room2, quiet=True, move_type="move", exit_obj=self.exit,
        )
        self.assertEqual(self.char1.move, char_move_before - 1)

    def test_mount_exhausted_blocks_movement(self):
        """Mount at 0 move should block movement."""
        horse = _make_horse(self.room1, self.char1)
        horse.mount(self.char1)
        horse.move = 0
        result = self.char1.at_pre_move(
            self.room2, move_type="move", exit_obj=self.exit,
        )
        self.assertFalse(result)

    def test_dismount_then_walk_uses_character_move(self):
        """After dismounting, movement should deduct from character again."""
        horse = _make_horse(self.room1, self.char1)
        horse.mount(self.char1)
        horse.dismount(self.char1)
        char_move_before = self.char1.move
        self.char1.move_to(
            self.room2, quiet=True, move_type="move", exit_obj=self.exit,
        )
        self.assertEqual(self.char1.move, char_move_before - 1)

    def test_horse_default_move(self):
        """Horse should have 300 base movement."""
        horse = _make_horse(self.room1, self.char1)
        self.assertEqual(horse.move, 300)
        self.assertEqual(horse.base_move_max, 300)
        self.assertEqual(horse.move_max, 300)


# ── NFTPetMirrorMixin Guards ─────────────────────────────────────────

class TestPetGuards(_PetTestBase):
    """Test NFTPetMirrorMixin guards."""

    def test_pet_cannot_enter_character_contents(self):
        """at_pre_move should block moves to character.contents."""
        mule = _make_mule(self.room1, self.char1)
        result = mule.at_pre_move(self.char1)
        self.assertFalse(result)

    def test_pet_cannot_be_picked_up(self):
        """at_pre_get should block pickup."""
        mule = _make_mule(self.room1, self.char1)
        result = mule.at_pre_get(self.char1)
        self.assertFalse(result)

    def test_resolve_owner_raises(self):
        """_resolve_owner should raise NotImplementedError on pets."""
        mule = _make_mule(self.room1, self.char1)
        with self.assertRaises(NotImplementedError):
            mule._resolve_owner(self.room1)

    def test_is_same_owner_raises(self):
        """_is_same_owner should raise NotImplementedError on pets."""
        mule = _make_mule(self.room1, self.char1)
        with self.assertRaises(NotImplementedError):
            mule._is_same_owner("ROOM", None, "ROOM", None)


# ── Dot Syntax ───────────────────────────────────────────────────────

class TestPetDotSyntax(_PetTestBase):
    """Test multi-pet dot syntax."""

    def test_dot_syntax_by_name(self):
        """pet.<name> should target specific pet."""
        mule = _make_mule(self.room1, self.char1)
        mule.key = "Bessie"
        result = self.call(CmdPet(), ".bessie status")
        self.assertIn("Bessie", result)

    def test_dot_syntax_by_type(self):
        """pet.<type> should target by pet_type."""
        _make_mule(self.room1, self.char1)
        result = self.call(CmdPet(), ".mule status")
        self.assertIn("mule", result.lower())

    def test_dot_syntax_unknown(self):
        """pet.<unknown> should show error."""
        _make_mule(self.room1, self.char1)
        result = self.call(CmdPet(), ".dragon status")
        self.assertIn("don't have a pet", result)
