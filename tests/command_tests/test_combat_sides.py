"""
Tests for dynamic combat side assignment.

Sides are assigned at combat entry based on who attacked who and
group membership — not actor type.

evennia test --settings settings tests.command_tests.test_combat_sides
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create


class TestCombatSides(EvenniaCommandTest):
    """Test dynamic combat side assignment via enter_combat / get_sides."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = False
        self.char1.hp = 20
        self.char1.hp_max = 20
        self.char2.hp = 20
        self.char2.hp_max = 20

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        # Clean up any extra actors stored as self._extras
        for obj in getattr(self, "_extras", []):
            handlers = obj.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
            obj.delete()
        super().tearDown()

    def _make_mob(self, key="test_mob", hp=20):
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key=key,
            location=self.room1,
        )
        mob.hp = hp
        mob.hp_max = hp
        if not hasattr(self, "_extras"):
            self._extras = []
        self._extras.append(mob)
        return mob

    # ── Basic 1v1 side assignment ─────────────────────────────────────

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_basic_1v1_opposite_sides(self, mock_ticker):
        """Combatant gets side 1, target gets side 2."""
        from combat.combat_utils import enter_combat, _get_combat_side

        mob = self._make_mob()
        enter_combat(self.char1, mob)

        self.assertEqual(_get_combat_side(self.char1), 1)
        self.assertEqual(_get_combat_side(mob), 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_get_sides_returns_correct_allies_enemies(self, mock_ticker):
        """get_sides uses stored combat_side, not actor type."""
        from combat.combat_utils import enter_combat, get_sides

        mob = self._make_mob()
        enter_combat(self.char1, mob)

        allies, enemies = get_sides(self.char1)
        self.assertIn(self.char1, allies)
        self.assertIn(mob, enemies)

        allies_m, enemies_m = get_sides(mob)
        self.assertIn(mob, allies_m)
        self.assertIn(self.char1, enemies_m)

    # ── Bystander joins by attacking ──────────────────────────────────

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_bystander_attacks_combatant_joins_opposite(self, mock_ticker):
        """Bystander attacking a side-1 combatant joins side 2."""
        from combat.combat_utils import enter_combat, get_sides, _get_combat_side

        mob = self._make_mob()
        enter_combat(self.char1, mob)  # char1=1, mob=2

        # char2 attacks char1 (side 1) → char2 should join side 2
        self.room1.allow_pvp = True  # needed for PC-vs-PC attack
        enter_combat(self.char2, self.char1)

        self.assertEqual(_get_combat_side(self.char2), 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_bystander_attacks_mob_joins_opposite(self, mock_ticker):
        """Second PC attacking the mob joins the PC's side."""
        from combat.combat_utils import enter_combat, get_sides, _get_combat_side

        mob = self._make_mob()
        enter_combat(self.char1, mob)  # char1=1, mob=2

        # char2 attacks mob (side 2) → char2 should join side 1
        enter_combat(self.char2, mob)

        self.assertEqual(_get_combat_side(self.char2), 1)

        # Verify get_sides sees both PCs as allies
        allies, enemies = get_sides(self.char1)
        self.assertIn(self.char1, allies)
        self.assertIn(self.char2, allies)
        self.assertIn(mob, enemies)

    # ── Combatant attacks bystander ───────────────────────────────────

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_combatant_attacks_bystander(self, mock_ticker):
        """Combatant attacking a bystander places bystander on opposite side."""
        from combat.combat_utils import enter_combat, _get_combat_side

        mob1 = self._make_mob("mob1")
        mob2 = self._make_mob("mob2")
        enter_combat(self.char1, mob1)  # char1=1, mob1=2

        # char1 (side 1) attacks mob2 (bystander) → mob2 should join side 2
        enter_combat(self.char1, mob2)

        self.assertEqual(_get_combat_side(mob2), 2)

    # ── Group auto-join ───────────────────────────────────────────────

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_group_follower_joins_leaders_side(self, mock_ticker):
        """Follower auto-joins on their leader's side."""
        from combat.combat_utils import enter_combat, _get_combat_side

        # char2 follows char1
        self.char2.following = self.char1

        mob = self._make_mob()
        enter_combat(self.char1, mob)  # char1=1, mob=2, char2 pulled in

        self.assertEqual(_get_combat_side(self.char1), 1)
        self.assertEqual(_get_combat_side(self.char2), 1)
        self.assertEqual(_get_combat_side(mob), 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_npc_following_pc_joins_pc_side(self, mock_ticker):
        """An NPC following a PC joins the PC's side."""
        from combat.combat_utils import enter_combat, _get_combat_side

        guard = self._make_mob("town guard")
        guard.following = self.char1  # guard follows PC

        mob = self._make_mob("goblin")
        enter_combat(self.char1, mob)  # char1=1, mob=2, guard pulled in on 1

        self.assertEqual(_get_combat_side(self.char1), 1)
        self.assertEqual(_get_combat_side(guard), 1)
        self.assertEqual(_get_combat_side(mob), 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_target_group_joins_target_side(self, mock_ticker):
        """Target's group members join the target's side."""
        from combat.combat_utils import enter_combat, _get_combat_side

        mob1 = self._make_mob("goblin1")
        mob2 = self._make_mob("goblin2")
        mob2.following = mob1  # mob2 follows mob1

        enter_combat(self.char1, mob1)  # char1=1, mob1=2, mob2 pulled in on 2

        self.assertEqual(_get_combat_side(mob1), 2)
        self.assertEqual(_get_combat_side(mob2), 2)

    # ── PvP room ──────────────────────────────────────────────────────

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_pvp_room_ffa(self, mock_ticker):
        """PvP room: everyone is an enemy regardless of side."""
        from combat.combat_utils import enter_combat, get_sides

        self.room1.allow_pvp = True
        mob = self._make_mob()
        enter_combat(self.char1, mob)

        allies, enemies = get_sides(self.char1)
        self.assertEqual(allies, [self.char1])
        self.assertIn(mob, enemies)

    # ── Existing handler keeps side ───────────────────────────────────

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_existing_handler_keeps_side(self, mock_ticker):
        """Re-entering combat doesn't flip an existing combatant's side."""
        from combat.combat_utils import enter_combat, _get_combat_side

        mob = self._make_mob()
        enter_combat(self.char1, mob)  # char1=1, mob=2

        # char1 is already on side 1. Another enter_combat shouldn't flip.
        mob2 = self._make_mob("mob2")
        enter_combat(self.char1, mob2)

        self.assertEqual(_get_combat_side(self.char1), 1)
        self.assertEqual(_get_combat_side(mob2), 2)

    # ── Combat end detection ──────────────────────────────────────────

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_combat_ends_when_enemies_dead(self, mock_ticker):
        """When all enemies die, combat ends for all allies."""
        from combat.combat_utils import enter_combat, get_sides

        mob = self._make_mob(hp=1)
        enter_combat(self.char1, mob)

        # Kill the mob
        mob.hp = 0

        # get_sides should return no enemies
        allies, enemies = get_sides(self.char1)
        self.assertEqual(len(enemies), 0)

    # ── Mob vs Mob ────────────────────────────────────────────────────

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_mob_vs_mob_opposite_sides(self, mock_ticker):
        """Two mobs can fight on opposite sides."""
        from combat.combat_utils import enter_combat, get_sides, _get_combat_side

        guard = self._make_mob("guard")
        goblin = self._make_mob("goblin")
        enter_combat(guard, goblin)

        self.assertEqual(_get_combat_side(guard), 1)
        self.assertEqual(_get_combat_side(goblin), 2)

        allies, enemies = get_sides(guard)
        self.assertIn(guard, allies)
        self.assertIn(goblin, enemies)

    # ── Bystander joins via group of existing combatant ───────────────

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_bystander_grouped_with_combatant_auto_sides(self, mock_ticker):
        """A bystander whose group leader is already fighting joins that side."""
        from combat.combat_utils import enter_combat, _get_combat_side

        mob = self._make_mob()
        enter_combat(self.char1, mob)  # char1=1, mob=2

        # char2 follows char1 AFTER combat started
        self.char2.following = self.char1

        # Now mob attacks char2 — char2 should join char1's side (1)
        enter_combat(mob, self.char2)

        self.assertEqual(_get_combat_side(self.char2), 1)

    # ── Edge cases: early returns from get_sides ──────────────────────

    def test_get_sides_no_location_returns_empty(self):
        """A combatant with no location returns ([], [])."""
        from combat.combat_utils import get_sides

        # Evennia's .location property: set to None to simulate an
        # actor that has been removed from the world.
        original = self.char1.location
        try:
            self.char1.location = None
            allies, enemies = get_sides(self.char1)
            self.assertEqual(allies, [])
            self.assertEqual(enemies, [])
        finally:
            self.char1.location = original

    def test_get_sides_not_in_combat_returns_empty(self):
        """A combatant not in combat (no combat_handler) returns ([], [])."""
        from combat.combat_utils import get_sides

        # char1 is in the room but has never entered combat — no
        # combat_handler script is attached, so _get_combat_side
        # returns 0 and the non-PvP branch returns ([], []).
        allies, enemies = get_sides(self.char1)
        self.assertEqual(allies, [])
        self.assertEqual(enemies, [])
