"""
Spell base class — all spells inherit from this.

Each spell is a singleton class registered via @register_spell.
The base class handles mastery validation, mana deduction, and
cooldown tracking; subclasses implement _execute() with spell-specific logic.

Spell effects scale with the caster's mastery tier in the spell's
school. This is why spells are class-based rather than data-driven —
each tier can have qualitatively different behavior (e.g. Teleport:
basic=within area, GM=across worlds).

_execute() returns (bool, dict) on success, where the dict contains
multi-perspective messages:
    {
        "first":  "You fire 3 missiles at goblin...",  # → caster
        "second": "Bob fires 3 missiles at you...",    # → target
        "third":  "Bob fires 3 missiles at goblin...", # → room
    }

cast() returns (False, str) on validation failure (caster-only message).

Cooldown system:
    Spells have a cooldown in combat rounds after casting. Default
    cooldowns are tier-based: BASIC/SKILLED=0, EXPERT=1, MASTER=2,
    GM=3. Override `cooldown` on a spell class to customise.
    Set to None to use the default tier-based value.

Usage:
    @register_spell
    class MagicMissile(Spell):
        key = "magic_missile"
        aliases = ["mm"]
        name = "Magic Missile"
        school = skills.EVOCATION
        min_mastery = MasteryLevel.BASIC
        mana_cost = {1: 5, 2: 8, 3: 12, 4: 16, 5: 20}
        target_type = "actor_hostile"

        def _execute(self, caster, target):
            ...
"""

from enum import Enum

from enums.mastery_level import MasteryLevel

# Default cooldowns by minimum mastery tier.
# BASIC/SKILLED = 0 rounds, EXPERT = 1, MASTER = 2, GM = 3.
_DEFAULT_COOLDOWNS = {
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 2,
    MasteryLevel.GRANDMASTER: 3,
}


class Spell:
    """
    Base class for all spells.

    Class attributes (override in subclass):
        key         — unique identifier, e.g. "magic_missile"
        aliases     — alternative names for matching, e.g. ["mm"]
        name        — display name, e.g. "Magic Missile"
        school      — skills enum member (e.g. skills.EVOCATION) or string
        min_mastery — minimum MasteryLevel to learn/cast
        mana_cost   — dict {mastery_tier_int: mana_cost}
        target_type — see below
        range — "self", "melee", or "ranged" (height gating)
        cooldown    — rounds of cooldown after casting (None = use default)
        description — short flavour text shown in spellbook/spellinfo
        mechanics   — multi-line rules/scaling text for spellinfo

    target_type values:
        Actor targets (resolved via caller.search() in cmd_cast / cmd_zap):
            "actor_hostile"  — an enemy in the room (target required)
            "actor_friendly" — an ally in the room (defaults to self if blank)
            "self"     — the caster, always
            "none"     — no target needed
            "actor_any" — any actor in the room

        Item targets (resolved via spell_utils.resolve_spell_target):
            "items_inventory"
                Inventory only (e.g. Create Water — fill a container).
            "items_all_room_then_inventory"
                Room (objects + exits) first, inventory fallback
                (e.g. Knock — unlock a door or chest).
            "items_inventory_then_all_room"
                Inventory first, room (objects + exits) fallback
                (e.g. Identify — inspect a looted item or a door).

        Item-target spells receive the resolved item as ``target`` in
        ``_execute()`` and dispatch on it via duck-typing rather than
        isinstance. The caller never sees the resolution failure
        message — the helper sends it directly.
    """

    key = ""
    aliases = []
    name = ""
    school = ""
    min_mastery = MasteryLevel.BASIC
    mana_cost = {}
    target_type = "actor_hostile"
    range = "ranged"        # "self", "melee", "ranged", or "ranged_only"
    aoe = None              # None / "unsafe" / "unsafe_self" / "safe" / "allies"
    medium = "air"          # "air" / "water" / "any"
    cooldown = None         # None = use default based on min_mastery tier
    has_spell_arg = False   # True = cmd_cast pops first word as spell_arg
    description = ""
    mechanics = ""

    @property
    def school_key(self):
        """Return string key for school — handles both enum and string."""
        return self.school.value if isinstance(self.school, Enum) else self.school

    def get_cooldown(self):
        """
        Return the cooldown in combat rounds for this spell.

        If cooldown is explicitly set on the class, use that.
        Otherwise, derive from min_mastery tier using defaults.
        """
        if self.cooldown is not None:
            return self.cooldown
        return _DEFAULT_COOLDOWNS.get(self.min_mastery, 0)

    def get_caster_tier(self, caster):
        """
        Look up the caster's mastery tier for this spell's school.

        Checks class_skill_mastery_levels (mage/cleric schools are class skills).
        Returns int (MasteryLevel.value): 0=UNSKILLED through 5=GRANDMASTER.

        Wand zap override: if ``caster.ndb._wand_caster_tier_override`` is set
        (an int), return that instead. This lets the zap command force wands
        to always cast at the spell's base min_mastery regardless of who holds
        them, without threading an override parameter through all 60+ spell
        subclasses.
        """
        override = getattr(caster.ndb, "_wand_caster_tier_override", None)
        if override is not None:
            return int(override)
        entry = (caster.db.class_skill_mastery_levels or {}).get(self.school_key)
        if not entry:
            return 0
        if hasattr(entry, "get"):
            return entry.get("mastery", 0)
        return entry

    def is_on_cooldown(self, caster):
        """
        Check if this spell is on cooldown for the caster.

        Returns (bool, int) — is on cooldown, rounds remaining.
        """
        cooldowns = caster.db.spell_cooldowns or {}
        remaining = cooldowns.get(self.key, 0)
        return remaining > 0, remaining

    def apply_cooldown(self, caster):
        """Set this spell's cooldown on the caster."""
        cd = self.get_cooldown()
        if cd <= 0:
            return
        cooldowns = dict(caster.db.spell_cooldowns or {})
        cooldowns[self.key] = cd
        caster.db.spell_cooldowns = cooldowns

    def cast(self, caster, target=None, spell_arg=None):
        """
        Validate mastery, cooldown, and mana, then dispatch to _execute.

        Args:
            caster: the actor casting the spell
            target: resolved target (or None)
            spell_arg: optional spell argument (e.g. element for Resist)

        Returns:
            (bool, str) on validation failure — caster-only error message
            (bool, dict) on spell execution — multi-perspective messages
        """
        tier = self.get_caster_tier(caster)
        if tier < self.min_mastery.value:
            return (False, "Your mastery is too low to cast this spell.")

        # Check cooldown
        on_cd, remaining = self.is_on_cooldown(caster)
        if on_cd:
            s = "s" if remaining != 1 else ""
            return (
                False,
                f"{self.name} is on cooldown ({remaining} round{s} remaining).",
            )

        # Height filtering for melee spells is primarily enforced at
        # resolution time in resolve_spell_target via p_same_height.
        # This belt-and-suspenders check catches direct cast() callers
        # (AI, scripts, tests) that bypass resolve_spell_target.
        if self.range == "melee" and target:
            caster_height = getattr(caster, "room_vertical_position", 0)
            target_height = getattr(target, "room_vertical_position", 0)
            if caster_height != target_height:
                return (
                    False,
                    "You can't reach them from your current height.",
                )

        cost = self.mana_cost.get(tier, 0)

        # Wand zap bypass: mana was pre-paid at enchant time.
        if getattr(caster.ndb, "_wand_free_cast", False):
            cost = 0

        if caster.mana < cost:
            return (
                False,
                f"Not enough mana (need {cost}, have {caster.mana}).",
            )

        caster.mana -= cost
        if self.has_spell_arg:
            result = self._execute(caster, target, spell_arg=spell_arg)
        else:
            result = self._execute(caster, target)

        # Apply cooldown on successful cast
        if result[0]:
            self.apply_cooldown(caster)

        return result

    def _execute(self, caster, target, spell_arg=None):
        """
        Execute the spell.

        Override in every spell subclass. Returns (bool, dict) where dict
        contains keys: "first" (caster), "second" (target), "third" (room).
        Set "second" to None for self-targeted spells.

        Args:
            spell_arg: optional argument parsed from cast command
                       (e.g. element for Resist). Only set when
                       has_spell_arg = True.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _execute()"
        )
