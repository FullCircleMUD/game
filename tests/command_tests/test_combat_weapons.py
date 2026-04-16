"""
Tests for weapon combat mechanics — parry, durability, crits, multi-attack,
finesse, hit bonuses, APR, rapier mastery and riposte.

evennia test --settings settings tests.command_tests.test_combat_weapons
"""

from unittest.mock import patch, MagicMock
from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create


# ================================================================== #
#  Parry Tests
# ================================================================== #


class TestParry(EvenniaCommandTest):
    """Test the parry system in execute_attack."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        self.char1.hp = 50
        self.char1.hp_max = 50
        self.char2.hp = 50
        self.char2.hp_max = 50

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        # Clean up weapons
        for obj in list(self.char1.contents) + list(self.char2.contents):
            if hasattr(obj, "weapon_type_key"):
                obj.delete()
        super().tearDown()

    def _equip_longsword(self, char, mastery_level):
        """Create a longsword and equip it on char with given mastery."""
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Longsword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        # Set mastery on character
        char.db.weapon_skill_mastery_levels = {
            "long_sword": mastery_level.value,
        }
        # Equip directly via wearslots
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_parry_blocks_melee_attack(self, mock_ticker):
        """SKILLED longsword wielder parries melee attack, blocking damage."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        attacker_sword = self._equip_longsword(self.char1, MasteryLevel.BASIC)
        defender_sword = self._equip_longsword(self.char2, MasteryLevel.SKILLED)
        enter_combat(self.char1, self.char2)

        # Set parries on defender
        defender_handler = self.char2.scripts.get("combat_handler")[0]
        defender_handler.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            # Attacker rolls 10, defender parry rolls high (25 > 10+bonuses)
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [10, 25]
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        # Target should take no damage (parried)
        self.assertEqual(self.char2.hp, 50)
        # Both weapons lose durability
        self.assertEqual(attacker_sword.durability, 99)
        self.assertEqual(defender_sword.durability, 99)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_parry_fails_attack_proceeds(self, mock_ticker):
        """Low parry roll doesn't block, attack resolves normally."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        self._equip_longsword(self.char2, MasteryLevel.SKILLED)
        enter_combat(self.char1, self.char2)

        defender_handler = self.char2.scripts.get("combat_handler")[0]
        defender_handler.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            # Attacker rolls 15, defender parry rolls low (2)
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [15, 2]
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        # Target should take damage (parry failed, attack hit)
        self.assertLess(self.char2.hp, 50)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_parry_not_triggered_unarmed_attacker(self, mock_ticker):
        """Unarmed attacker doesn't trigger parry (weapon is None)."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        # Only defender has weapon
        self._equip_longsword(self.char2, MasteryLevel.SKILLED)
        enter_combat(self.char1, self.char2)

        defender_handler = self.char2.scripts.get("combat_handler")[0]
        defender_handler.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        # Attack should resolve normally (parry not attempted)
        self.assertLess(self.char2.hp, 50)
        # Parry not consumed
        self.assertEqual(defender_handler.parries_remaining, 1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_parry_uses_remaining_count(self, mock_ticker):
        """After all parries consumed, further attacks are not parried."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        self._equip_longsword(self.char2, MasteryLevel.SKILLED)
        enter_combat(self.char1, self.char2)

        defender_handler = self.char2.scripts.get("combat_handler")[0]
        defender_handler.parries_remaining = 1

        # First attack: parried (high parry roll)
        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [10, 25]
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        self.assertEqual(self.char2.hp, 50)  # no damage
        self.assertEqual(defender_handler.parries_remaining, 0)

        # Second attack: no parry available
        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        self.assertLess(self.char2.hp, 50)  # damage dealt

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_parry_resets_each_round(self, mock_ticker):
        """Parries reset at start of execute_next_action."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat

        self._equip_longsword(self.char1, MasteryLevel.SKILLED)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]

        # Exhaust parries
        handler.parries_remaining = 0

        # Execute next action resets parries based on weapon
        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 1
            handler.execute_next_action()

        # SKILLED longsword = 1 parry per round
        self.assertEqual(handler.parries_remaining, 1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_grandmaster_parry_advantage(self, mock_ticker):
        """Grandmaster longsword gets parry_advantage set on handler."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat

        self._equip_longsword(self.char1, MasteryLevel.GRANDMASTER)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 1
            handler.execute_next_action()

        self.assertTrue(handler.parry_advantage)
        self.assertEqual(handler.parries_remaining, 3)


# ================================================================== #
#  Durability Tests
# ================================================================== #


class TestCombatDurability(EvenniaCommandTest):
    """Test durability loss during combat."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        self.char1.hp = 50
        self.char1.hp_max = 50
        self.char2.hp = 50
        self.char2.hp_max = 50

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        for obj in list(self.char1.contents) + list(self.char2.contents):
            if hasattr(obj, "weapon_type_key") or getattr(obj, "wearslot", None):
                obj.delete()
        super().tearDown()

    def _equip_weapon(self, char):
        """Create and equip a basic longsword."""
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Sword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    def _equip_armor(self, char, slot="BODY"):
        """Create and equip body armor or helmet."""
        from enums.wearslot import HumanoidWearSlot
        armor = create.create_object(
            "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
            key=f"Test {'Helmet' if slot == 'HEAD' else 'Armor'}",
            location=char,
        )
        armor.wearslot = HumanoidWearSlot.HEAD if slot == "HEAD" else HumanoidWearSlot.BODY
        armor.max_durability = 80
        armor.durability = 80
        wearslots = dict(char.db.wearslots or {})
        wearslots[slot] = armor
        char.db.wearslots = wearslots
        return armor

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_hit_reduces_weapon_durability(self, mock_ticker):
        """Attacker's weapon loses 1 durability on hit."""
        from combat.combat_utils import enter_combat, execute_attack

        weapon = self._equip_weapon(self.char1)
        enter_combat(self.char1, self.char2)

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        self.assertEqual(weapon.durability, 99)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_hit_reduces_body_armor_durability(self, mock_ticker):
        """Target's body armor loses 1 durability on hit."""
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_weapon(self.char1)
        armor = self._equip_armor(self.char2, "BODY")
        enter_combat(self.char1, self.char2)

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        self.assertEqual(armor.durability, 79)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_miss_no_durability_loss(self, mock_ticker):
        """No durability change on miss."""
        from combat.combat_utils import enter_combat, execute_attack

        weapon = self._equip_weapon(self.char1)
        armor = self._equip_armor(self.char2, "BODY")
        enter_combat(self.char1, self.char2)
        self.char2.armor_class = 100  # guarantee miss

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 1
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        self.assertEqual(weapon.durability, 100)
        self.assertEqual(armor.durability, 80)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_parry_both_weapons_lose_durability(self, mock_ticker):
        """Both weapons lose 1 durability on successful parry."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        atk_sword = self._equip_weapon(self.char1)
        def_sword = self._equip_weapon(self.char2)
        self.char2.db.weapon_skill_mastery_levels = {"long_sword": MasteryLevel.SKILLED.value}
        enter_combat(self.char1, self.char2)

        defender_handler = self.char2.scripts.get("combat_handler")[0]
        defender_handler.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [10, 25]
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        self.assertEqual(atk_sword.durability, 99)
        self.assertEqual(def_sword.durability, 99)
        self.assertEqual(self.char2.hp, 50)  # no damage


# ================================================================== #
#  CRIT_IMMUNE Tests
# ================================================================== #


class TestCritImmune(EvenniaCommandTest):
    """Test CRIT_IMMUNE condition in combat."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        self.char1.hp = 50
        self.char1.hp_max = 50
        self.char2.hp = 50
        self.char2.hp_max = 50

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        for obj in list(self.char1.contents) + list(self.char2.contents):
            if hasattr(obj, "weapon_type_key") or getattr(obj, "wearslot", None):
                obj.delete()
        super().tearDown()

    def _equip_weapon(self, char):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Sword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    def _equip_armor(self, char, slot="BODY"):
        from enums.wearslot import HumanoidWearSlot
        armor = create.create_object(
            "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
            key=f"Test {'Helmet' if slot == 'HEAD' else 'Armor'}",
            location=char,
        )
        armor.wearslot = HumanoidWearSlot.HEAD if slot == "HEAD" else HumanoidWearSlot.BODY
        armor.max_durability = 80
        armor.durability = 80
        wearslots = dict(char.db.wearslots or {})
        wearslots[slot] = armor
        char.db.wearslots = wearslots
        return armor

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_crit_immune_downgrades_to_normal_hit(self, mock_ticker):
        """CRIT_IMMUNE downgrades crit to normal hit (no double dice)."""
        from enums.condition import Condition
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_weapon(self.char1)
        self._equip_armor(self.char2, "HEAD")
        enter_combat(self.char1, self.char2)

        # Give target CRIT_IMMUNE condition
        self.char2.add_condition(Condition.CRIT_IMMUNE)
        # Set crit threshold low so d20=15 is a crit
        self.char1.base_crit_threshold = 15

        with patch("combat.combat_utils.dice") as mock_dice:
            # d20=15 (would be crit), damage roll=5
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        # Should have taken damage but NOT double dice
        # dice.roll called only once (not twice as it would for crit)
        self.assertEqual(mock_dice.roll.call_count, 1)
        self.assertLess(self.char2.hp, 50)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_crit_immune_helmet_takes_durability(self, mock_ticker):
        """CRIT_IMMUNE: helmet -1 durability, body armor spared."""
        from enums.condition import Condition
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_weapon(self.char1)
        body_armor = self._equip_armor(self.char2, "BODY")
        helmet = self._equip_armor(self.char2, "HEAD")
        enter_combat(self.char1, self.char2)

        self.char2.add_condition(Condition.CRIT_IMMUNE)
        self.char1.base_crit_threshold = 15

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        # Helmet takes durability, body armor does not
        self.assertEqual(helmet.durability, 79)
        self.assertEqual(body_armor.durability, 80)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_crit_without_crit_immune(self, mock_ticker):
        """Normal crit deals double dice and body armor takes durability."""
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_weapon(self.char1)
        body_armor = self._equip_armor(self.char2, "BODY")
        helmet = self._equip_armor(self.char2, "HEAD")
        enter_combat(self.char1, self.char2)

        self.char1.base_crit_threshold = 15

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        # dice.roll called twice (damage + crit bonus)
        self.assertEqual(mock_dice.roll.call_count, 2)
        # Body armor takes durability, helmet does not
        self.assertEqual(body_armor.durability, 79)
        self.assertEqual(helmet.durability, 80)


# ================================================================== #
#  Multi-Attack Tests
# ================================================================== #


class TestMultiAttack(EvenniaCommandTest):
    """Test extra attacks from weapon mastery."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        self.char1.hp = 50
        self.char1.hp_max = 50
        self.char2.hp = 50
        self.char2.hp_max = 50

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        for obj in list(self.char1.contents) + list(self.char2.contents):
            if hasattr(obj, "weapon_type_key"):
                obj.delete()
        super().tearDown()

    def _equip_longsword(self, char, mastery_level):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Longsword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        char.db.weapon_skill_mastery_levels = {"long_sword": mastery_level.value}
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_master_longsword_extra_attack(self, mock_ticker):
        """Master longsword fires 2 attacks per tick."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.MASTER)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 3, "repeat": True,
        })

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch("combat.combat_utils.execute_attack", wraps=execute_attack) as spy:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            handler.execute_next_action()

        # execute_attack should have been called twice
        self.assertEqual(spy.call_count, 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_basic_longsword_single_attack(self, mock_ticker):
        """Basic longsword fires only 1 attack per tick."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 3, "repeat": True,
        })

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch("combat.combat_utils.execute_attack", wraps=execute_attack) as spy:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            handler.execute_next_action()

        self.assertEqual(spy.call_count, 1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_extra_attack_stops_on_kill(self, mock_ticker):
        """Second attack doesn't fire if target dies on first."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat

        self._equip_longsword(self.char1, MasteryLevel.MASTER)
        enter_combat(self.char1, self.char2)
        self.char2.hp = 1  # Will die on first hit

        handler = self.char1.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 3, "repeat": True,
        })

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch.object(self.char2, "die") as mock_die:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 10
            handler.execute_next_action()

        # die() called only once (second attack skipped)
        mock_die.assert_called_once_with("combat", killer=self.char1)


# ================================================================== #
#  Longsword Custom Hit Bonus Tests
# ================================================================== #


class TestLongswordHitBonuses(EvenniaCommandTest):
    """Test longsword custom hit bonuses override defaults."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_longsword_custom_hit_bonuses(self):
        """Longsword hit bonuses differ from default mastery bonuses."""
        from enums.mastery_level import MasteryLevel
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Longsword",
            location=self.char1,
        )
        try:
            # MASTER: longsword=+4, default=+6
            self.char1.db.weapon_skill_mastery_levels = {"long_sword": MasteryLevel.MASTER.value}
            self.assertEqual(sword.get_mastery_hit_bonus(self.char1), 4)
            self.assertNotEqual(MasteryLevel.MASTER.bonus, 4)  # default is 6

            # GRANDMASTER: longsword=+5, default=+8
            self.char1.db.weapon_skill_mastery_levels = {"long_sword": MasteryLevel.GRANDMASTER.value}
            self.assertEqual(sword.get_mastery_hit_bonus(self.char1), 5)
            self.assertNotEqual(MasteryLevel.GRANDMASTER.bonus, 5)  # default is 8

            # SKILLED: longsword=+2, same as default
            self.char1.db.weapon_skill_mastery_levels = {"long_sword": MasteryLevel.SKILLED.value}
            self.assertEqual(sword.get_mastery_hit_bonus(self.char1), 2)
        finally:
            sword.delete()


# ================================================================== #
#  Effective Attacks Per Round Tests
# ================================================================== #


class TestEffectiveAttacksPerRound(EvenniaCommandTest):
    """Test effective_attacks_per_round property and HASTED integration."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        self.char1.hp = 50
        self.char1.hp_max = 50
        self.char2.hp = 50
        self.char2.hp_max = 50

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        for obj in list(self.char1.contents) + list(self.char2.contents):
            if hasattr(obj, "weapon_type_key"):
                obj.delete()
        super().tearDown()

    def _equip_longsword(self, char, mastery_level):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Longsword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        char.db.weapon_skill_mastery_levels = {"long_sword": mastery_level.value}
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    def test_base_attacks_no_weapon(self):
        """No weapon: effective_attacks_per_round equals attacks_per_round."""
        self.assertEqual(self.char1.attacks_per_round, 1)
        self.assertEqual(self.char1.effective_attacks_per_round, 1)

    def test_basic_weapon_no_extra_attacks(self):
        """Basic longsword gives no extra attacks."""
        from enums.mastery_level import MasteryLevel
        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        self.assertEqual(self.char1.effective_attacks_per_round, 1)

    def test_master_weapon_extra_attack(self):
        """Master longsword adds 1 extra attack via effective_attacks_per_round."""
        from enums.mastery_level import MasteryLevel
        self._equip_longsword(self.char1, MasteryLevel.MASTER)
        self.assertEqual(self.char1.effective_attacks_per_round, 2)

    def test_hasted_adds_one_attack(self):
        """HASTED condition adds 1 to attacks_per_round, reflected in effective."""
        from enums.condition import Condition
        newly_gained = self.char1.add_condition(Condition.HASTED)
        self.assertTrue(newly_gained)
        self.char1.apply_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.assertEqual(self.char1.attacks_per_round, 2)
        self.assertEqual(self.char1.effective_attacks_per_round, 2)
        # Clean up
        self.char1.remove_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.char1.remove_condition(Condition.HASTED)

    def test_hasted_plus_master_weapon(self):
        """HASTED + master longsword = 3 attacks per round."""
        from enums.condition import Condition
        from enums.mastery_level import MasteryLevel
        self._equip_longsword(self.char1, MasteryLevel.MASTER)
        self.char1.add_condition(Condition.HASTED)
        self.char1.apply_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.assertEqual(self.char1.effective_attacks_per_round, 3)
        # Clean up
        self.char1.remove_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.char1.remove_condition(Condition.HASTED)

    def test_hasted_does_not_stack(self):
        """Two sources of HASTED still only give 1 extra attack."""
        from enums.condition import Condition
        # First source: newly gained, apply effect
        gained1 = self.char1.add_condition(Condition.HASTED)
        self.assertTrue(gained1)
        if gained1:
            self.char1.apply_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})

        # Second source: NOT newly gained, do NOT apply effect
        gained2 = self.char1.add_condition(Condition.HASTED)
        self.assertFalse(gained2)
        if gained2:
            self.char1.apply_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})

        # Count is 2, but attacks_per_round only got +1
        self.assertEqual(self.char1.get_condition_count(Condition.HASTED), 2)
        self.assertEqual(self.char1.attacks_per_round, 2)  # base 1 + 1 from haste
        self.assertEqual(self.char1.effective_attacks_per_round, 2)

        # Remove first source: count drops to 1, effect stays
        removed1 = self.char1.remove_condition(Condition.HASTED)
        self.assertFalse(removed1)
        if removed1:
            self.char1.remove_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.assertEqual(self.char1.attacks_per_round, 2)  # still have the bonus

        # Remove second source: fully removed, now remove effect
        removed2 = self.char1.remove_condition(Condition.HASTED)
        self.assertTrue(removed2)
        if removed2:
            self.char1.remove_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.assertEqual(self.char1.attacks_per_round, 1)  # back to base
        self.assertEqual(self.char1.effective_attacks_per_round, 1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_hasted_master_fires_three_attacks(self, mock_ticker):
        """HASTED + master longsword fires 3 attacks in combat handler."""
        from enums.condition import Condition
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.MASTER)
        self.char1.add_condition(Condition.HASTED)
        self.char1.apply_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})

        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 3, "repeat": True,
        })

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch("combat.combat_utils.execute_attack", wraps=execute_attack) as spy:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            handler.execute_next_action()

        self.assertEqual(spy.call_count, 3)

        # Clean up
        self.char1.remove_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.char1.remove_condition(Condition.HASTED)


# ================================================================== #
#  Finesse Weapon Tests
# ================================================================== #


class TestFinesseWeapons(EvenniaCommandTest):
    """Test finesse weapon mechanics — uses max(STR, DEX) for hit/damage."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def tearDown(self):
        for obj in list(self.char1.contents):
            if hasattr(obj, "weapon_type_key"):
                obj.delete()
        super().tearDown()

    def _equip_rapier(self, char):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        rapier = create.create_object(
            "typeclasses.items.weapons.rapier_nft_item.RapierNFTItem",
            key="Test Rapier",
            location=char,
        )
        rapier.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        rapier.damage_type = DamageType.PIERCING
        rapier.max_durability = 100
        rapier.durability = 100
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = rapier
        char.db.wearslots = wearslots
        return rapier

    def _equip_longsword(self, char):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Longsword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    def test_finesse_uses_dex_when_higher(self):
        """Finesse weapon uses DEX when DEX > STR."""
        self._equip_rapier(self.char1)
        self.char1.strength = 10   # mod +0
        self.char1.dexterity = 16  # mod +3
        hit_dex = self.char1.effective_hit_bonus
        dam_dex = self.char1.effective_damage_bonus
        # Swap: STR high, DEX low — should give same result since max() picks higher
        self.char1.strength = 16   # mod +3
        self.char1.dexterity = 10  # mod +0
        hit_str = self.char1.effective_hit_bonus
        dam_str = self.char1.effective_damage_bonus
        self.assertEqual(hit_dex, hit_str)
        self.assertEqual(dam_dex, dam_str)

    def test_finesse_uses_str_when_higher(self):
        """Finesse weapon uses STR when STR > DEX."""
        self._equip_rapier(self.char1)
        self.char1.strength = 18   # mod +4
        self.char1.dexterity = 12  # mod +1
        hit = self.char1.effective_hit_bonus
        # Confirm STR mod is being used (not DEX mod)
        expected_str_mod = self.char1.get_attribute_bonus(18)  # +4
        expected_dex_mod = self.char1.get_attribute_bonus(12)  # +1
        self.assertGreater(expected_str_mod, expected_dex_mod)
        # Lower STR to match DEX — hit should drop
        self.char1.strength = 12
        hit_lower = self.char1.effective_hit_bonus
        self.assertGreater(hit, hit_lower)

    def test_non_finesse_always_uses_str(self):
        """Non-finesse melee weapon always uses STR regardless of DEX."""
        self._equip_longsword(self.char1)
        self.char1.strength = 10   # mod +0
        self.char1.dexterity = 18  # mod +4
        hit_low_str = self.char1.effective_hit_bonus
        self.char1.strength = 18   # mod +4
        hit_high_str = self.char1.effective_hit_bonus
        # Longsword uses STR only — higher STR = higher bonus
        self.assertGreater(hit_high_str, hit_low_str)

    def test_finesse_flag_on_rapier(self):
        """RapierNFTItem has is_finesse = True."""
        rapier = self._equip_rapier(self.char1)
        self.assertTrue(rapier.is_finesse)

    def test_finesse_flag_off_on_longsword(self):
        """LongswordNFTItem has is_finesse = False."""
        sword = self._equip_longsword(self.char1)
        self.assertFalse(sword.is_finesse)


# ================================================================== #
#  Rapier Mastery & Riposte Tests
# ================================================================== #


class TestRapierMastery(EvenniaCommandTest):
    """Test rapier mastery progression and riposte mechanic."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.char1.hp = 50
        self.char1.hp_max = 50
        self.char2.hp = 50
        self.char2.hp_max = 50

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        for obj in list(self.char1.contents) + list(self.char2.contents):
            if hasattr(obj, "weapon_type_key"):
                obj.delete()
        super().tearDown()

    def _equip_rapier(self, char, mastery_level):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        rapier = create.create_object(
            "typeclasses.items.weapons.rapier_nft_item.RapierNFTItem",
            key="Test Rapier",
            location=char,
        )
        rapier.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        rapier.damage_type = DamageType.PIERCING
        rapier.max_durability = 100
        rapier.durability = 100
        char.db.weapon_skill_mastery_levels = {"rapier": mastery_level.value}
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = rapier
        char.db.wearslots = wearslots
        return rapier

    def _equip_longsword(self, char, mastery_level):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Longsword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        char.db.weapon_skill_mastery_levels = {"long_sword": mastery_level.value}
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    # --- Mastery table tests ---

    def test_rapier_custom_hit_bonuses(self):
        """Rapier has reduced hit bonuses at EXPERT+ to offset riposte."""
        from enums.mastery_level import MasteryLevel
        rapier = self._equip_rapier(self.char1, MasteryLevel.EXPERT)
        self.assertEqual(rapier.get_mastery_hit_bonus(self.char1), 3)
        self.char1.db.weapon_skill_mastery_levels = {"rapier": MasteryLevel.MASTER.value}
        self.assertEqual(rapier.get_mastery_hit_bonus(self.char1), 4)
        self.char1.db.weapon_skill_mastery_levels = {"rapier": MasteryLevel.GRANDMASTER.value}
        self.assertEqual(rapier.get_mastery_hit_bonus(self.char1), 5)

    def test_rapier_parries_per_round(self):
        """Rapier parry progression: 0/0/1/1/2/3."""
        from enums.mastery_level import MasteryLevel
        rapier = self._equip_rapier(self.char1, MasteryLevel.UNSKILLED)
        expected = [
            (MasteryLevel.UNSKILLED, 0),
            (MasteryLevel.BASIC, 0),
            (MasteryLevel.SKILLED, 1),
            (MasteryLevel.EXPERT, 1),
            (MasteryLevel.MASTER, 2),
            (MasteryLevel.GRANDMASTER, 3),
        ]
        for mastery, count in expected:
            self.char1.db.weapon_skill_mastery_levels = {"rapier": mastery.value}
            self.assertEqual(
                rapier.get_parries_per_round(self.char1), count,
                f"Expected {count} parries at {mastery.name}, got {rapier.get_parries_per_round(self.char1)}",
            )

    def test_rapier_no_extra_attacks(self):
        """Rapier never grants extra attacks (that's the longsword's thing)."""
        from enums.mastery_level import MasteryLevel
        rapier = self._equip_rapier(self.char1, MasteryLevel.GRANDMASTER)
        self.assertEqual(rapier.get_extra_attacks(self.char1), 0)

    def test_rapier_riposte_unlocks_at_expert(self):
        """has_riposte returns False below EXPERT, True at EXPERT+."""
        from enums.mastery_level import MasteryLevel
        rapier = self._equip_rapier(self.char1, MasteryLevel.SKILLED)
        self.assertFalse(rapier.has_riposte(self.char1))
        self.char1.db.weapon_skill_mastery_levels = {"rapier": MasteryLevel.EXPERT.value}
        self.assertTrue(rapier.has_riposte(self.char1))
        self.char1.db.weapon_skill_mastery_levels = {"rapier": MasteryLevel.MASTER.value}
        self.assertTrue(rapier.has_riposte(self.char1))
        self.char1.db.weapon_skill_mastery_levels = {"rapier": MasteryLevel.GRANDMASTER.value}
        self.assertTrue(rapier.has_riposte(self.char1))

    def test_rapier_parry_advantage_at_gm(self):
        """Rapier gets parry advantage only at GRANDMASTER."""
        from enums.mastery_level import MasteryLevel
        rapier = self._equip_rapier(self.char1, MasteryLevel.MASTER)
        self.assertFalse(rapier.get_parry_advantage(self.char1))
        self.char1.db.weapon_skill_mastery_levels = {"rapier": MasteryLevel.GRANDMASTER.value}
        self.assertTrue(rapier.get_parry_advantage(self.char1))

    def test_longsword_no_riposte(self):
        """Longsword never has riposte — base weapon default is False."""
        from enums.mastery_level import MasteryLevel
        sword = self._equip_longsword(self.char1, MasteryLevel.GRANDMASTER)
        self.assertFalse(sword.has_riposte(self.char1))

    # --- Riposte in combat tests ---

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_riposte_fires_on_successful_parry(self, mock_ticker):
        """Expert rapier wielder ripostes after a successful parry."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        # char1 attacks with longsword, char2 defends with expert rapier
        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        rapier = self._equip_rapier(self.char2, MasteryLevel.EXPERT)

        enter_combat(self.char1, self.char2)
        # Set up char2's parries (normally reset each tick)
        handler2 = self.char2.scripts.get("combat_handler")[0]
        handler2.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            # First call: attacker's d20 = 10 (low, easy to parry)
            # Second call: defender parry d20 = 20 (parry succeeds)
            # Third call: riposte attacker d20 = 15 (riposte hit roll)
            # roll calls: damage rolls
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [10, 20, 15]
            mock_dice.roll.return_value = 5

            initial_hp = self.char1.hp
            execute_attack(self.char1, self.char2)

        # char2 should have taken no damage (parried)
        self.assertEqual(self.char2.hp, 50)
        # char1 should have taken riposte damage
        self.assertLess(self.char1.hp, initial_hp)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_no_riposte_at_skilled(self, mock_ticker):
        """Skilled rapier wielder parries but does NOT riposte."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        self._equip_rapier(self.char2, MasteryLevel.SKILLED)

        enter_combat(self.char1, self.char2)
        handler2 = self.char2.scripts.get("combat_handler")[0]
        handler2.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            # Attacker d20 = 10, parry d20 = 20 (parry succeeds)
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [10, 20]
            mock_dice.roll.return_value = 5

            execute_attack(self.char1, self.char2)

        # char2 parried — no damage
        self.assertEqual(self.char2.hp, 50)
        # char1 took no riposte damage (SKILLED has no riposte)
        self.assertEqual(self.char1.hp, 50)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_riposte_cannot_be_parried(self, mock_ticker):
        """Riposte attacks skip the parry check (_is_riposte=True)."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        # Both wield rapiers at expert — both have riposte
        self._equip_rapier(self.char1, MasteryLevel.EXPERT)
        self._equip_rapier(self.char2, MasteryLevel.EXPERT)

        enter_combat(self.char1, self.char2)
        handler1 = self.char1.scripts.get("combat_handler")[0]
        handler2 = self.char2.scripts.get("combat_handler")[0]
        handler1.parries_remaining = 1
        handler2.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            # Call 1: char1's attack d20 = 10
            # Call 2: char2's parry d20 = 20 (parry succeeds)
            # Call 3: char2's riposte d20 = 15 (this is _is_riposte=True, no parry check)
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [10, 20, 15]
            mock_dice.roll.return_value = 5

            execute_attack(self.char1, self.char2)

        # char2 parried, so no damage from char1
        self.assertEqual(self.char2.hp, 50)
        # char1 took riposte damage — even though char1 had parries remaining,
        # riposte attacks skip the parry check
        self.assertLess(self.char1.hp, 50)
        # char1's parries_remaining should still be 1 (not consumed by riposte)
        self.assertEqual(handler1.parries_remaining, 1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_master_rapier_multiple_ripostes(self, mock_ticker):
        """Master rapier with 2 parries can riposte twice against multiple attacks."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        # char1 attacks with longsword (master = 2 attacks per round)
        self._equip_longsword(self.char1, MasteryLevel.MASTER)
        self._equip_rapier(self.char2, MasteryLevel.MASTER)

        enter_combat(self.char1, self.char2)
        handler2 = self.char2.scripts.get("combat_handler")[0]
        handler2.parries_remaining = 2

        riposte_count = 0
        original_execute = execute_attack

        def counting_execute(a, t, _is_riposte=False):
            nonlocal riposte_count
            if _is_riposte:
                riposte_count += 1
            return original_execute(a, t, _is_riposte=_is_riposte)

        with patch("combat.combat_utils.dice") as mock_dice:
            # Attack 1: d20=10, parry=20 (parry+riposte), riposte d20=15
            # Attack 2: d20=10, parry=20 (parry+riposte), riposte d20=15
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [
                10, 20, 15,  # attack 1 → parry → riposte
                10, 20, 15,  # attack 2 → parry → riposte
            ]
            mock_dice.roll.return_value = 3

            # Patch execute_attack at the module level to count ripostes
            with patch("combat.combat_utils.execute_attack", side_effect=counting_execute):
                # Call the original for the two main attacks
                for _ in range(2):
                    if self.char2.hp > 0 and self.char1.hp > 0:
                        original_execute(self.char1, self.char2)

        self.assertEqual(riposte_count, 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_riposte_does_not_fire_if_parry_fails(self, mock_ticker):
        """Failed parry does not trigger riposte."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        self._equip_rapier(self.char2, MasteryLevel.EXPERT)

        enter_combat(self.char1, self.char2)
        handler2 = self.char2.scripts.get("combat_handler")[0]
        handler2.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            # Attacker d20 = 20 (high roll), parry d20 = 5 (parry fails)
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [20, 5]
            mock_dice.roll.return_value = 3

            initial_hp1 = self.char1.hp
            execute_attack(self.char1, self.char2)

        # char1 should NOT have taken riposte damage (parry failed)
        self.assertEqual(self.char1.hp, initial_hp1)
        # char2 should have taken damage (attack hit)
        self.assertLess(self.char2.hp, 50)
