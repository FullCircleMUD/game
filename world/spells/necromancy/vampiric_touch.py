"""
Vampiric Touch — necromancy spell, available from SKILLED mastery.

The addictive drain spell. Unlike Drain Life (which caps at max HP),
Vampiric Touch can raise the caster's HP ABOVE their maximum. This
creates the classic necromancer drain tank fantasy — but with a catch.

MELEE RANGE — forces the necro to get close for the good stuff.

Mechanic:
    - Touch attack: d20 + INT mod + mastery bonus vs target AC
    - Deals necrotic damage, heals caster for 100% (can exceed max HP)
    - Applies VAMPIRIC effect tracking bonus HP and timer
    - 10 minute duration — resets on each successful drain
    - When timer expires: ALL bonus HP lost instantly (floor at 1 HP)
    - Escalating mana cost based on current bonus HP bracket

The addiction: the more you drain, the more expensive each cast
becomes, AND you can't stop or you lose everything. The stereotypical
lust for power which becomes a prison.

Damage (starter scaling: +1d6/tier from SKILLED):
    SKILLED(2): 1d6 necrotic
    EXPERT(3):  2d6 necrotic
    MASTER(4):  3d6 necrotic
    GM(5):      4d6 necrotic

Mana cost: percentage of max mana, scaling exponentially with bonus HP.
    +0 to +99:     3% of max mana
    +100 to +199:   6%
    +200 to +299:  10%
    +300 to +399:  16%
    +400 to +499:  24%
    +500 to +599:  34%
    +600 to +699:  46%
    +700 to +799:  60%
    +800 to +899:  78%
    +900 to +999:  95%
    +1000:        101% (impossible — hard cap)

Cooldown: 0 (need to spam it to build up).
"""

from evennia.scripts.scripts import DefaultScript

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell
from world.spells.spell_utils import apply_spell_damage


# Mana cost as % of max mana per bonus HP bracket (0-indexed by hundreds)
_MANA_COST_PCT = [3, 6, 10, 16, 24, 34, 46, 60, 78, 95, 101]

# Touch attack mastery hit bonus (INT mod added separately)
_MASTERY_HIT_BONUS = {2: 1, 3: 2, 4: 3, 5: 4}

# Timer duration: 10 minutes
_VAMPIRIC_DURATION = 600


class VampiricTimerScript(DefaultScript):
    """
    One-shot timer attached to a caster with VAMPIRIC effect.

    When the timer fires (10 minutes after last drain), all bonus HP
    is stripped and the caster drops to a minimum of 1 HP.

    Reset on each successful Vampiric Touch drain via restart().
    """

    def at_script_creation(self):
        self.key = "vampiric_timer"
        self.desc = "Vampiric Touch expiry timer"
        self.interval = _VAMPIRIC_DURATION
        self.start_delay = True
        self.persistent = True
        self.repeats = 1  # fire once

    def at_repeat(self):
        """Timer expired — strip bonus HP and remove VAMPIRIC effect."""
        caster = self.obj
        if not caster:
            return

        bonus_hp = caster.db.vampiric_bonus_hp or 0
        if bonus_hp > 0:
            caster.hp = max(1, caster.hp - bonus_hp)
        caster.attributes.remove("vampiric_bonus_hp")

        if hasattr(caster, "remove_named_effect"):
            caster.remove_named_effect("vampiric")


@register_spell
class VampiricTouch(Spell):
    key = "vampiric_touch"
    aliases = ["vt", "vamp"]
    name = "Vampiric Touch"
    school = skills.NECROMANCY
    min_mastery = MasteryLevel.SKILLED
    # Mana cost is dynamic — base class mana_cost set to 0 so cast()
    # deducts nothing; we handle mana in our override.
    mana_cost = {2: 0, 3: 0, 4: 0, 5: 0}
    target_type = "hostile"
    spell_range = "melee"
    cooldown = 0
    description = "Drains life through touch, raising your HP beyond its maximum."
    mechanics = (
        "MELEE RANGE — must be adjacent to target.\n"
        "Touch attack: d20 + INT mod + mastery bonus vs target AC.\n"
        "Deals necrotic damage and heals you for 100%, even above max HP.\n"
        "Applies VAMPIRIC effect: 10 minute timer, resets each drain.\n"
        "When timer expires: ALL bonus HP lost (minimum 1 HP).\n"
        "Mana cost escalates with bonus HP: 3% at +0, up to 95% at +900.\n"
        "Hard cap: +1000 bonus HP (cost exceeds 100% max mana).\n"
        "Damage: 1d6 (Skilled) to 4d6 (Grandmaster) necrotic.\n"
        "No cooldown."
    )

    # Dice per tier: base 1d6 at SKILLED, +1d6 per tier (starter)
    _DICE = {2: 1, 3: 2, 4: 3, 5: 4}

    def _get_mana_cost(self, caster):
        """
        Calculate dynamic mana cost based on current bonus HP bracket.

        Returns (cost, error_msg) — error_msg is None if affordable.
        """
        bonus_hp = caster.db.vampiric_bonus_hp or 0
        bracket = min(bonus_hp // 100, len(_MANA_COST_PCT) - 1)
        cost_pct = _MANA_COST_PCT[bracket]

        if cost_pct > 100:
            return 0, (
                "You've pushed too far — the hunger exceeds "
                "your ability to sustain it."
            )

        actual_cost = max(1, int(caster.mana_max * cost_pct / 100))

        if caster.mana < actual_cost:
            return actual_cost, (
                f"Not enough mana (need {actual_cost}, have {caster.mana})."
            )

        return actual_cost, None

    def cast(self, caster, target=None, spell_arg=None):
        """
        Override cast() for dynamic mana cost.

        Base class uses static mana_cost dict; we calculate cost from
        the caster's current bonus HP bracket instead.
        """
        tier = self.get_caster_tier(caster)
        if tier < self.min_mastery.value:
            return (False, "Your mastery is too low to cast this spell.")

        # Height check — melee range spell
        if target:
            caster_height = getattr(caster, "room_vertical_position", 0)
            target_height = getattr(target, "room_vertical_position", 0)
            if caster_height != target_height:
                return (
                    False,
                    "You can't reach them from your current height.",
                )

        on_cd, remaining = self.is_on_cooldown(caster)
        if on_cd:
            s = "s" if remaining != 1 else ""
            return (
                False,
                f"{self.name} is on cooldown ({remaining} round{s} remaining).",
            )

        # Dynamic mana cost
        actual_cost, error = self._get_mana_cost(caster)
        if error:
            return (False, error)

        caster.mana -= actual_cost
        result = self._execute(caster, target)

        if result[0]:
            self.apply_cooldown(caster)

        return result

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)

        # --- Touch attack roll ---
        attack_roll = dice.roll("1d20")
        int_mod = caster.get_attribute_bonus(caster.intelligence)
        mastery_bonus = _MASTERY_HIT_BONUS.get(tier, 0)
        total_hit = attack_roll + int_mod + mastery_bonus
        target_ac = target.effective_ac

        if total_hit < target_ac:
            return (True, {
                "first": (
                    f"|rYour vampiric touch misses {target.key}! "
                    f"(rolled {total_hit} vs AC {target_ac})|n"
                ),
                "second": (
                    f"|r{caster.key} reaches toward you with dark energy "
                    f"but misses!|n"
                ),
                "third": (
                    f"|r{caster.key} reaches toward {target.key} with dark "
                    f"energy but misses!|n"
                ),
            })

        # --- Damage ---
        num_dice = self._DICE.get(tier, 4)
        raw_damage = dice.roll(f"{num_dice}d6")
        actual_damage = apply_spell_damage(target, raw_damage, DamageType.NECROTIC)

        # --- Heal caster (no max HP cap) ---
        hp_before = caster.hp
        caster.hp += actual_damage

        # Track bonus HP (amount above effective max)
        effective_max = caster.effective_hp_max
        if caster.hp > effective_max:
            # New total bonus = current HP - effective max
            caster.db.vampiric_bonus_hp = caster.hp - effective_max
        # If still below max, just normal healing (no bonus HP to track)

        heal_amount = caster.hp - hp_before
        bonus_hp = caster.db.vampiric_bonus_hp or 0

        # --- Apply/reset VAMPIRIC effect and timer ---
        self._apply_vampiric_effect(caster)

        # --- Build messages ---
        bonus_msg = ""
        if bonus_hp > 0:
            bonus_msg = f" |M(+{bonus_hp} bonus HP)|n"

        return (True, {
            "first": (
                f"|rYour vampiric touch drains {target.key}, dealing "
                f"{actual_damage} necrotic damage and healing you for "
                f"|g{heal_amount}|r HP!{bonus_msg}|n"
            ),
            "second": (
                f"|r{caster.key}'s deathly touch drains your life force, "
                f"dealing {actual_damage} necrotic damage!|n"
            ),
            "third": (
                f"|r{caster.key}'s vampiric touch drains {target.key} "
                f"for {actual_damage} necrotic damage!|n"
            ),
        })

    def _apply_vampiric_effect(self, caster):
        """Apply or refresh the VAMPIRIC named effect and timer."""
        if not caster.has_effect("vampiric"):
            # First cast — apply the effect (no duration, script manages it)
            caster.apply_vampiric(source=caster)

        # Create or reset the timer script
        existing = caster.scripts.get("vampiric_timer")
        if existing:
            # Reset timer to full 10 minutes
            script = existing[0]
            script.restart(interval=_VAMPIRIC_DURATION)
        else:
            # Create new timer script
            from evennia.utils.create import create_script
            script = create_script(
                VampiricTimerScript,
                obj=caster,
                key="vampiric_timer",
                autostart=False,
            )
            script.interval = _VAMPIRIC_DURATION
            script.start()


def remove_vampiric(caster):
    """
    Utility to cleanly remove Vampiric Touch effect and bonus HP.

    Called by dispel magic, death, or any other forced removal.
    Strips bonus HP (floor at 1 HP) and cleans up the timer script.
    """
    bonus_hp = caster.db.vampiric_bonus_hp or 0
    if bonus_hp > 0:
        caster.hp = max(1, caster.hp - bonus_hp)
    caster.attributes.remove("vampiric_bonus_hp")

    if hasattr(caster, "remove_named_effect"):
        caster.remove_named_effect("vampiric")

    existing = caster.scripts.get("vampiric_timer")
    if existing:
        existing[0].delete()
