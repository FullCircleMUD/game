"""
Relieve Hunger — divine_healing spell, available from BASIC mastery.

A cleric-side survival utility that restores hunger levels directly.
Symmetric with forage's hunger restoration and with Create Water's
mastery scaling — BASIC +1 level, GM +5 levels — so the three survival
utilities (forage, Create Water, Relieve Hunger) share an intentional
design shape across druid/ranger, mage, and cleric classes.

Scaling:
    BASIC(1):   +1 level, caster only,                     5 mana
    SKILLED(2): +2 levels, caster only,                    8 mana
    EXPERT(3):  +3 levels, caster only,                   12 mana
    MASTER(4):  +4 levels, caster + same-room group,      16 mana
    GM(5):      +5 levels, caster + same-room group,      20 mana

Caster-only at low tiers, group at MASTER+ (mirroring shadowcloak's
same-room group targeting). Reuses `_get_group_targets` from
shadowcloak to resolve party membership.

IMPORTANT: does NOT create bread. Restores the meter directly in the
same way forage does, without producing a tradeable resource. This is
the deliberate economic safety: farming/milling/baking still has AMM
dominance, but a cleric party can survive extended field trips without
needing a druid or a canteen of water.

No hunger_free_pass_tick is set — bread retains its advantage on the
just-ate edge case, same rule forage uses.

Cooldown: 0 (utility spell, spammable — gated by mana cost).
"""

from enums.hunger_level import HungerLevel
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.abjuration.shadowcloak import _get_group_targets
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


_GROUP_TIER_THRESHOLD = 4  # MASTER and above get group targeting


@register_spell
class RelieveHunger(Spell):
    key = "relieve_hunger"
    aliases = ["satiate", "rh"]
    name = "Relieve Hunger"
    school = skills.DIVINE_HEALING
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 12, 4: 16, 5: 20}
    target_type = "none"
    cooldown = 0
    description = "Channels divine sustenance to quell hunger in yourself or your flock."
    mechanics = (
        "Restores hunger levels directly — does NOT create bread.\n"
        "BASIC(1):      +1 level, caster only.\n"
        "SKILLED(2):    +2 levels, caster only.\n"
        "EXPERT(3):     +3 levels, caster only.\n"
        "MASTER(4):     +4 levels, caster + same-room group members.\n"
        "GRANDMASTER(5): +5 levels, caster + same-room group members.\n"
        "Each target is capped at FULL. Refunds mana if no one needs feeding.\n"
        "No cooldown — gated by mana cost."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        points = tier  # BASIC=1 ... GM=5

        if tier >= _GROUP_TIER_THRESHOLD:
            targets = _get_group_targets(caster)
        else:
            targets = [caster]

        needy = [t for t in targets if self._needs_feeding(t)]

        if not needy:
            # Everyone's already full — refund mana.
            caster.mana += self.mana_cost.get(tier, 0)
            if len(targets) == 1:
                first = "You are already full."
            else:
                first = "Your flock is already satiated."
            return (False, {"first": first, "second": None, "third": None})

        fed = []  # list of (target, restored_count)
        for t in needy:
            current = t.hunger_level
            new_value = min(current.value + points, HungerLevel.FULL.value)
            t.hunger_level = HungerLevel(new_value)
            # NO hunger_free_pass_tick — bread retains its advantage,
            # same rule forage uses.
            restored = new_value - current.value
            fed.append((t, restored))

        return self._build_messages(caster, fed)

    @staticmethod
    def _needs_feeding(actor):
        """True if the actor has a hunger meter below FULL."""
        hunger = getattr(actor, "hunger_level", None)
        if not isinstance(hunger, HungerLevel):
            return False
        return hunger.value < HungerLevel.FULL.value

    @staticmethod
    def _build_messages(caster, fed):
        """
        Build a multi-perspective message dict for a successful cast.

        Solo fed list (caster only) uses a terse self-heal style matching
        Cure Wounds. Group fed list produces a caster-facing summary and
        a per-ally nudge (delivered via the spell framework's multi-target
        messaging — or directly on each target via `.msg()`).
        """
        if len(fed) == 1 and fed[0][0] == caster:
            _, restored = fed[0]
            return (True, {
                "first": (
                    f"|gDivine warmth fills your belly. (+{restored} hunger "
                    f"level{'s' if restored != 1 else ''})|n"
                ),
                "second": None,
                "third": (
                    f"|g{caster.key} closes their eyes in prayer, and a "
                    f"warm glow briefly suffuses them.|n"
                ),
            })

        # Group cast — nudge each non-caster ally directly, then build the
        # caster-facing summary and the room-facing flavour line.
        for t, restored in fed:
            if t == caster:
                continue
            t.msg(
                f"|g{caster.key}'s prayer fills you with warmth. "
                f"(+{restored} hunger level{'s' if restored != 1 else ''})|n"
            )

        ally_count = sum(1 for t, _ in fed if t != caster)
        caster_restored = next(
            (r for t, r in fed if t == caster), 0
        )

        if caster_restored > 0:
            first_self = (
                f"(+{caster_restored} hunger "
                f"level{'s' if caster_restored != 1 else ''} for you, "
            )
        else:
            first_self = "(you are already full, "

        first = (
            f"|gYou channel divine sustenance over your flock. {first_self}"
            f"{ally_count} {'ally' if ally_count == 1 else 'allies'} fed)|n"
        )
        third = (
            f"|g{caster.key} raises their hands in prayer. A warm glow "
            f"washes over the group.|n"
        )

        return (True, {"first": first, "second": None, "third": third})
