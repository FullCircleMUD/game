"""
Shadowcloak — abjuration spell, available from SKILLED mastery.

Group stealth buff. Wraps the caster and all same-room group members
in a cloak of shadows, granting a bonus to stealth_bonus for a
duration that scales with mastery.

If the caster is solo (not in a follow chain), the spell applies to
self only. If the caster is in a group, it applies to all same-room
group members (leader + followers).

Scaling:
    SKILLED(2): +4 stealth_bonus,  4 minutes, mana 12
    EXPERT(3):  +6 stealth_bonus,  6 minutes, mana 15
    MASTER(4):  +8 stealth_bonus,  8 minutes, mana 20
    GM(5):      +10 stealth_bonus, 10 minutes, mana 24

Duration is wall-clock (seconds-based). Each group member gets their
own independent timer via apply_named_effect().

Anti-stacking: targets that already have the shadowcloaked effect are
skipped. Mana is not refunded for skipped targets (partial application
is fine for group spells). If ALL targets are already affected, mana
is refunded.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# Stealth bonus per tier
_BONUS = {2: 4, 3: 6, 4: 8, 5: 10}

# Duration in minutes per tier
_DURATION = {2: 4, 3: 6, 4: 8, 5: 10}

# Mana cost per tier
_MANA = {2: 12, 3: 15, 4: 20, 5: 24}


def _get_group_targets(caster):
    """Return a list of all group members in the same room, including caster.

    If the caster is not in a follow chain, returns [caster].
    """
    leader = caster.get_group_leader()

    # If leader == caster and no followers, solo cast
    followers = leader.get_followers(same_room=True)

    targets = []
    # Add the leader if they're in the same room as the caster
    if leader.location == caster.location:
        targets.append(leader)
    # Add followers that are in the same room
    for f in followers:
        if f not in targets:
            targets.append(f)
    # Ensure caster is always included
    if caster not in targets:
        targets.append(caster)

    return targets


@register_spell
class Shadowcloak(Spell):
    key = "shadowcloak"
    aliases = ["sc"]
    name = "Shadowcloak"
    school = skills.ABJURATION
    min_mastery = MasteryLevel.SKILLED
    mana_cost = _MANA
    target_type = "none"
    cooldown = 0
    description = "Wraps you and your group in a cloak of shadows, boosting stealth."
    mechanics = (
        "Usage: cast shadowcloak\n"
        "Applies to self if solo, or all same-room group members.\n"
        "Skilled: +4 stealth, 4 min. Expert: +6, 6 min. "
        "Master: +8, 8 min. Grandmaster: +10, 10 min.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        bonus = _BONUS.get(tier, 4)
        duration_minutes = _DURATION.get(tier, 4)
        duration_seconds = duration_minutes * 60

        # Resolve group targets
        targets = _get_group_targets(caster)

        # Filter out targets that already have the effect
        new_targets = [t for t in targets if not t.has_effect("shadowcloaked")]

        if not new_targets:
            # Everyone already has the effect — refund mana
            caster.mana += self.mana_cost.get(tier, 0)
            if len(targets) == 1:
                return (False, {
                    "first": "You are already cloaked in shadows.",
                    "second": None,
                    "third": None,
                })
            return (False, {
                "first": "Your group is already cloaked in shadows.",
                "second": None,
                "third": None,
            })

        # Apply the effect to each new target
        for t in new_targets:
            t.apply_shadowcloaked(bonus, duration_seconds, source=caster)

        # Build cast messages
        is_group = len(new_targets) > 1
        ally_count = len(new_targets) - 1  # exclude caster

        if is_group:
            first_msg = (
                f"|CYou extend a cloak of shadows over your group. "
                f"(+{bonus} stealth, {duration_minutes} min, "
                f"{ally_count} {'ally' if ally_count == 1 else 'allies'})|n"
            )
            third_msg = (
                f"|C{caster.key} weaves shadows around their group.|n"
            )
        else:
            first_msg = (
                f"|CYou wrap yourself in a cloak of shadows. "
                f"(+{bonus} stealth, {duration_minutes} min)|n"
            )
            third_msg = (
                f"|C{caster.key} weaves shadows around themselves.|n"
            )

        return (True, {
            "first": first_msg,
            "second": None,
            "third": third_msg,
        })
