"""
Tests for BaseWearslotsMixin.worn_summary — what a looker learns about an
actor's kit when they look at them.

Two gates, asked in that order. Sight belongs to the looker, so it is
asked once and suppresses the whole block: blind, or in a dark room
without darkvision, and no kit list appears. Concealment belongs to each
item, so it is asked per slot and the list shortens.

evennia test --settings settings tests.typeclass_tests.test_worn_summary
"""

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
from enums.wearslot import HumanoidWearSlot


class MobEquipmentTest(EvenniaTest):
    """An armed bandit in a lit room, and someone looking at it."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.mob = create.create_object(
            "typeclasses.actors.mobs.tights_bandit.TightsBandit",
            key="a bandit in striped tights",
            location=self.room1,
            nohome=True,
        )
        self.mob.is_alive = True

    def tearDown(self):
        if self.mob.pk:
            self.mob.delete()
        super().tearDown()

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False

    def _shown(self):
        return self.mob.worn_summary(self.char1)

    def _worn_items(self):
        return [
            item for item in self.mob.get_all_worn().values()
            if item is not None
        ]


class TestWhatIsListed(MobEquipmentTest):

    def test_the_bandit_arrives_armed(self):
        """Guards the rest of the file — TightsBandit wears a shortsword."""
        self.assertTrue(self._worn_items())

    def test_worn_equipment_is_listed(self):
        shown = self._shown()
        for item in self._worn_items():
            self.assertIn(item.key, shown)

    def test_the_mob_is_named(self):
        self.assertIn(self.mob.key, self._shown())

    def test_an_unarmed_mob_shows_nothing(self):
        for item in self._worn_items():
            item.delete()
        self.assertEqual(self._shown(), "")

    def test_a_mob_without_wearslots_has_no_summary(self):
        """An actor that cannot wear anything has no kit to render.

        The renderer lives on the wearslots mixin, so a mob composing no
        wearslots simply does not have the method — which is what
        return_appearance's hasattr guard is asking.
        """
        plain = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a sewer rat",
            location=self.room1,
            nohome=True,
        )
        self.assertFalse(hasattr(plain, "worn_summary"))
        self.assertNotIn("is equipped with", plain.return_appearance(self.char1))

    def test_it_reaches_the_appearance(self):
        """The method is only useful through return_appearance."""
        text = self.mob.return_appearance(self.char1)
        self.assertIn("is equipped with", text)

    def test_a_player_gets_one_too(self):
        """Same mixin, so looking at another player reads the same way."""
        sword = create.create_object(
            "typeclasses.items.weapons.weapon_nft_item.WeaponNFTItem",
            key="a plain longsword",
            location=self.char2,
            nohome=True,
        )
        worn, why = self.char2.wear(sword)
        self.assertTrue(worn, why)
        self.assertIn(sword.key, self.char2.worn_summary(self.char1))


class TestSightGate(MobEquipmentTest):
    """
    Asked once for the whole list. A kit list is detail, and detail is
    exactly what darkness takes away.
    """

    def test_a_blinded_looker_sees_no_kit(self):
        self.char1.add_condition(Condition.BLINDED)
        self.assertEqual(self._shown(), "")

    def test_a_dark_room_shows_no_kit(self):
        self._darken()
        self.assertEqual(self._shown(), "")

    def test_darkvision_restores_it(self):
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        self.assertTrue(self._shown())

    def test_the_appearance_loses_the_block_in_the_dark(self):
        self._darken()
        text = self.mob.return_appearance(self.char1)
        self.assertNotIn("is equipped with", text)

    def test_the_mob_being_blind_changes_nothing(self):
        """It is the looker's eyes that matter, not the mob's."""
        self.mob.add_condition(Condition.BLINDED)
        self.assertTrue(self._shown())


class TestConcealmentGate(MobEquipmentTest):
    """
    Asked per item, and rendered as "Something" rather than dropped —
    the same masking ``equipment_cmd_output`` uses, since both views come
    off ``visible_item_name``.
    """

    def setUp(self):
        super().setUp()
        # A cloak rather than a weapon — the bandit's WIELD slot is taken,
        # and the kit needs a second item so the masking can be seen
        # against something unmasked.
        self.hideable = create.create_object(
            "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
            key="a shadowed cloak",
            location=self.mob,
            nohome=True,
            attributes=[("wearslot", HumanoidWearSlot.CLOAK.value)],
        )
        worn, why = self.mob.wear(self.hideable)
        self.assertTrue(worn, why)

    def tearDown(self):
        if self.hideable.pk:
            self.hideable.delete()
        super().tearDown()

    def test_an_unhidden_item_is_listed(self):
        self.assertIn(self.hideable.key, self._shown())

    def test_a_hidden_item_loses_its_name(self):
        self.hideable.is_hidden = True
        self.assertNotIn(self.hideable.key, self._shown())

    def test_a_hidden_item_keeps_its_place(self):
        """You can tell the slot is filled, not what fills it."""
        self.hideable.is_hidden = True
        self.assertIn(self.hideable.unseen_name, self._shown())

    def test_the_item_chooses_its_own_placeholder(self):
        """The word is content — a spawn rule can set it per instance."""
        self.hideable.unseen_name = "a shape beneath the cloak"
        self.hideable.is_hidden = True
        self.assertIn("a shape beneath the cloak", self._shown())

    def test_the_rest_of_the_kit_is_unaffected(self):
        """Masking is per item — the visible ones keep their names."""
        self.hideable.is_hidden = True
        shown = self._shown()
        for item in self._worn_items():
            if item is not self.hideable:
                self.assertIn(item.key, shown)

    def test_true_sight_restores_it(self):
        self.hideable.is_hidden = True
        self.char1.apply_true_sight(duration_seconds=300)
        self.assertIn(self.hideable.key, self._shown())

    def test_discovering_it_restores_it(self):
        self.hideable.is_hidden = True
        self.hideable.discover(self.char1)
        self.assertIn(self.hideable.key, self._shown())

    def test_a_wholly_concealed_kit_still_lists_placeholders(self):
        """Concealment masks; it does not empty the block.

        An armed stranger you cannot identify is still visibly armed —
        the alternative reads as an unarmed one.
        """
        for item in self._worn_items():
            if item is not self.hideable:
                item.delete()
        self.hideable.is_hidden = True
        shown = self._shown()
        self.assertIn("is equipped with", shown)
        self.assertIn(self.hideable.unseen_name, shown)
