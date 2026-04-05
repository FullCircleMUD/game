"""
Named effects — effects managed by EffectsManagerMixin.apply_named_effect().

Named effects have lifecycle management (combat rounds, seconds, or permanent),
anti-stacking, and automatic cleanup. They are the MANDATORY system for any
timed or tracked effect on an actor.

For condition flags (ref-counted, checked via has_condition()), see enums/condition.py.
Some effects appear in BOTH enums — e.g. SLOWED is a named effect for lifecycle
management AND a condition flag for gameplay checks (future movement speed system).

For effects not yet classified, see the UNSORTED EFFECTS comment block at the
bottom of this file. All effects MUST be classified before implementation.

apply_named_effect() validates the key against this enum — unknown keys are rejected.
"""

from enum import Enum

from enums.condition import Condition


class NamedEffect(Enum):

    #########################################################
    # Movement / Action Denial
    #########################################################
    # APPLIED: unarmed_weapon.py (_apply_stun) — mastery-scaled unarmed combat
    # CHECKED: combat_handler.py (has_effect skips action in execute_next_action)
    # DURATION: 1-2 combat rounds (mastery-scaled: SKILLED=1, GM=2)
    # No condition flag — purely named effect. Action denial only.
    STUNNED = "stunned"

    # APPLIED: unarmed_weapon.py (_apply_prone) — mastery-scaled unarmed combat
    # CHECKED: combat_handler.py (has_effect skips action in execute_next_action)
    # DURATION: 1 combat round. Also grants advantage to all attackers in room.
    # No condition flag — purely named effect. Action denial + advantage grant.
    PRONE = "prone"

    # APPLIED: cone_of_cold.py — evocation AoE spell
    # CHECKED: combat_handler.py (has_effect skips action — future: movement speed)
    # DURATION: 3 combat rounds. ALSO sets Condition.SLOWED flag (see condition.py).
    # Dual-system: named effect for lifecycle + condition flag for future movement checks.
    SLOWED = "slowed"

    # APPLIED: blowgun_nft_item.py (at_hit) — CON save on hit
    # CHECKED: combat_handler.py (has_effect skips action in execute_next_action)
    # DURATION: 1-3 combat rounds (mastery-scaled: BASIC/SKILLED=1, EXPERT/MASTER=2, GM=3)
    # Dual-system: named effect for lifecycle + Condition.PARALYSED for spell targeting.
    # Size-gated: HUGE+ enemies are immune. Grants advantage to all enemies.
    PARALYSED = "paralysed"

    # APPLIED: bola_nft_item.py (at_hit) — contested DEX roll on hit
    # CHECKED: combat_handler.py (has_effect skips action in execute_next_action)
    # DURATION: 1-6 combat rounds (mastery-scaled max), save-each-round STR escape
    # No condition flag — purely named effect. Action denial + advantage grant.
    # Size-gated: HUGE+ enemies are immune.
    ENTANGLED = "entangled"

    #########################################################
    # Damage Over Time
    #########################################################
    # APPLIED: blowgun_nft_item.py (at_hit) — poison dart on hit
    # CHECKED: has_effect("poisoned") for anti-stacking, Remove Poison spell targeting
    # DURATION: 1d3 to 1d4+3 ticks (mastery-scaled). Duration type forked at apply
    #   time: combat_rounds if target is in combat, seconds if not.
    # No condition flag — NamedEffect only. Uses PoisonDoTScript for per-tick damage.
    # NOT cleared by clear_combat_effects() when seconds-based (stealth poison edge case).
    POISONED = "poisoned"

    # APPLIED: acid_arrow.py (_execute) — conjuration workhorse spell
    # CHECKED: has_effect("acid_arrow") for anti-stacking (new cast replaces old)
    # DURATION: 1-5 combat rounds (mastery-scaled: tier = rounds).
    #   duration_type=None — AcidDoTScript manages lifecycle, not the effect system.
    # No condition flag — NamedEffect only. Uses AcidDoTScript for per-tick damage.
    # Each tick deals 1d4+1 acid damage. Same total damage budget as Magic Missile.
    ACID_ARROW = "acid_arrow"

    #########################################################
    # Defensive / Abjuration
    #########################################################
    # APPLIED: reactive_spells.py (check_reactive_shield) — auto-cast on hit
    # CHECKED: reactive_spells.py (has_effect for anti-stacking), combat_handler.py (tick)
    # DURATION: 1-3 combat rounds (mastery-scaled: BASIC +4/1, SKILLED +4/2,
    #   EXPERT +5/2, MASTER +5/3, GM +6/3). Reactive-only — cannot be cast manually.
    # No mana cost. No condition flag — AC bonus via stat_bonus effect.
    SHIELD = "shield"

    # APPLIED: mage_armor.py, divine_armor.py — manually cast self-buff
    # CHECKED: has_effect("armored") for anti-stacking (shared by both spells)
    # DURATION: seconds-based timer (wall-clock). Scaling varies by spell.
    # AC bonus via stat_bonus effect. Stacks with Shield.
    # Shared by Mage Armor (abjuration) and Divine Armor (divine protection).
    # No condition flag — AC bonus via stat_bonus effect.
    ARMORED = "armored"

    # APPLIED: shadowcloak.py (_execute) — group stealth buff
    # CHECKED: has_effect("shadowcloaked") for anti-stacking
    # DURATION: 4-10 minutes (mastery-scaled: SKILLED 4min, EXPERT 6min,
    #   MASTER 8min, GM 10min). Uses seconds-based timer (wall-clock).
    # Stealth bonus scales: SKILLED +4, EXPERT +6, MASTER +8, GM +10.
    # Group spell: applies to caster + all same-room group members.
    # No condition flag — stealth_bonus via stat_bonus effect.
    SHADOWCLOAKED = "shadowcloaked"

    #########################################################
    # Resistance Buffs (Abjuration)
    #########################################################
    # APPLIED: resist_elements.py (_execute) — abjuration buff, self or friendly
    # CHECKED: has_effect() for anti-stacking (per element)
    # DURATION: 30 seconds (wall-clock). duration_type="seconds".
    # Each element is a separate named effect — multiple resists can coexist.
    # No condition flag — damage_resistance via effects= param (Layer 2).
    RESIST_FIRE = "resist_fire"
    RESIST_COLD = "resist_cold"
    RESIST_LIGHTNING = "resist_lightning"
    RESIST_ACID = "resist_acid"
    RESIST_POISON = "resist_poison"

    #########################################################
    # Divination / Perception
    #########################################################
    # APPLIED: true_sight.py (_execute) — divination self-buff
    # CHECKED: has_effect("true_sight") for hidden detection in room_base.py,
    #   hidden_object.py. Also sets Condition.DETECT_INVIS for
    #   invisible detection (existing infrastructure handles that).
    # DURATION: 5-60 minutes (mastery-scaled: SKILLED=5min, GM=60min).
    #   duration_type="seconds" — EffectTimerScript handles expiry.
    # Dual-system: named effect for hidden detection + condition for invisible.
    # Does NOT remove HIDDEN from targets — only lets the caster see them.
    TRUE_SIGHT = "true_sight"

    # APPLIED: holy_sight.py (_execute) — divine revelation self-buff
    # CHECKED: has_effect("holy_sight") for hidden detection (MASTER+) in
    #   room_base.py, hidden_object.py. Also sets Condition.DETECT_INVIS
    #   at EXPERT+ (earlier than True Sight's MASTER+).
    # DURATION: 5-60 minutes (mastery-scaled, same as True Sight).
    # Tier order differs from True Sight: traps → invis → hidden.
    HOLY_SIGHT = "holy_sight"

    #########################################################
    # Illusion / Evasion
    #########################################################
    # APPLIED: blur.py (_execute) — illusion workhorse self-buff
    # CHECKED: has_effect("blurred") for anti-stacking (recast refreshes)
    # DURATION: 3-7 combat rounds (mastery-scaled: BASIC=3, GM=7).
    #   duration_type="combat_rounds" — auto-cleaned on combat end.
    # No condition flag — NamedEffect only. Uses BlurScript to set 1 disadvantage
    # on all enemies per combat round. Multi-attackers only lose accuracy on 1 attack/round.
    BLURRED = "blurred"

    # APPLIED: invisibility.py (_execute) — illusion self-buff
    # CHECKED: has_effect("invisible") for break-on-action in cmd_attack.py,
    #   cmd_cast.py, combat_utils.py. Also sets Condition.INVISIBLE for
    #   visibility filtering (existing infrastructure handles that).
    # DURATION: 5-60 minutes (mastery-scaled: SKILLED=5min, GM=60min).
    #   duration_type="seconds" — EffectTimerScript handles expiry.
    # Dual-system: named effect for lifecycle + condition for visibility.
    # Breaks on attack (grants advantage) or offensive spell cast.
    # NO anti-stacking — condition-only flag with no stat impact (see CLAUDE.md).
    INVISIBLE = "invisible"

    #########################################################
    # Potion Buffs (seconds-based, anti-stacking by stat)
    #########################################################
    # APPLIED: potion_nft_item.py (at_consume) — via apply_named_effect()
    # CHECKED: has_effect() for anti-stacking (can't drink same stat potion twice)
    # DURATION: 60-300 seconds (mastery-scaled: BASIC 60s to GM 300s)
    # No condition flag — purely stat_bonus effects.
    # Anti-stacking is by STAT, not by potion name — any two STR potions share
    # the same key and can't stack regardless of tier.
    POTION_STRENGTH = "potion_strength"
    POTION_DEXTERITY = "potion_dexterity"
    POTION_CONSTITUTION = "potion_constitution"
    POTION_INTELLIGENCE = "potion_intelligence"
    POTION_WISDOM = "potion_wisdom"
    POTION_CHARISMA = "potion_charisma"

    #########################################################
    # Combat Stances (Strategist)
    #########################################################
    # APPLIED: cmd_offence.py — group offensive stance toggle
    # CHECKED: has_effect() for toggle / mutual exclusion with defensive
    # DURATION: combat_rounds with duration=None — permanent until toggled off or combat ends
    # No condition flag — stat bonuses via effects= param (total_hit_bonus, total_damage_bonus, armor_class)
    OFFENSIVE_STANCE = "offensive_stance"

    # APPLIED: cmd_defence.py — group defensive stance toggle
    # CHECKED: has_effect() for toggle / mutual exclusion with offensive
    # DURATION: combat_rounds with duration=None — permanent until toggled off or combat ends
    # No condition flag — stat bonuses via effects= param (armor_class, total_hit_bonus)
    DEFENSIVE_STANCE = "defensive_stance"

    #########################################################
    # Weapon Mastery Debuffs
    #########################################################
    # APPLIED: axe_nft_item.py, battleaxe_nft_item.py (at_hit) — mastery-scaled
    # CHECKED: has_effect("sundered") for stack management (remove + reapply)
    # DURATION: 99 combat rounds (effectively rest of combat)
    # No condition flag — AC penalty via stat_bonus effect.
    # STACKING: each sunder removes old effect, reapplies with cumulative penalty.
    #   Tracked via target.db.sunder_stacks. AC floor = 10.
    #   Also deals extra durability damage to body armour on each proc.
    SUNDERED = "sundered"

    # APPLIED: club_nft_item.py, greatclub_nft_item.py (at_hit) — mastery-scaled
    # CHECKED: has_effect("staggered") for anti-stacking
    # DURATION: 1-2 combat rounds (club=1, greatclub=1-2 at MASTER+)
    # No condition flag — hit penalty via stat_bonus effect (total_hit_bonus).
    # NOT stacking — anti-stacking via has_effect check.
    STAGGERED = "staggered"

    #########################################################
    # Necromancy Spell Effects
    #########################################################
    # APPLIED: vampiric_touch.py (_execute) — necromancy drain-tank spell
    # CHECKED: has_effect("vampiric") for timer reset on recast, status display
    # DURATION: permanent until VampiricTimerScript fires (600s, resets each drain)
    # No condition flag — NamedEffect only. Bonus HP tracked via db.vampiric_bonus_hp.
    # On expiry: bonus HP lost, caster drops to min 1 HP.
    VAMPIRIC = "vampiric"

    #########################################################
    # Divine Judgement
    #########################################################
    # APPLIED: bravery.py (_execute) — paladin self-buff
    # CHECKED: has_effect("bravery") for anti-stacking
    # DURATION: 5-15 minutes (mastery-scaled). Uses seconds-based timer.
    # AC bonus + hp_max bonus via stat_bonus effects. HP clamped on expiry.
    BRAVERY = "bravery"

    #########################################################
    # Divine Protection
    #########################################################
    # APPLIED: sanctuary.py (_execute) — divine protection self-buff
    # CHECKED: combat_utils.py (target protection — block attack),
    #   cmd_cast.py (break on offensive cast), break_sanctuary() on attack
    # DURATION: 60-300 seconds (mastery-scaled: BASIC 1min to GM 5min).
    #   duration_type="seconds" — EffectTimerScript handles expiry.
    # Dual-system: named effect for lifecycle + Condition.SANCTUARY for combat checks.
    # Breaks on offensive action (attack or hostile spell cast).
    SANCTUARY = "sanctuary"

    # Test-only entry for unit tests
    POTION_TEST = "potion_test"

    # ------------------------------------------------------------------ #
    #  Message methods — same interface as Condition enum
    # ------------------------------------------------------------------ #

    def get_start_message(self) -> str:
        """Get the first-person message shown when this effect begins."""
        return _NAMED_EFFECT_START_MESSAGES.get(
            self, f"You are now affected by {self.value}."
        )

    def get_end_message(self) -> str:
        """Get the first-person message shown when this effect ends."""
        return _NAMED_EFFECT_END_MESSAGES.get(
            self, f"You are no longer affected by {self.value}."
        )

    def get_start_message_third_person(self, character_name: str) -> str:
        """Get the third-person message shown to others when this effect begins."""
        template = _NAMED_EFFECT_START_MESSAGES_THIRD_PERSON.get(
            self, f"{character_name} is now affected by {self.value}."
        )
        return template.format(name=character_name)

    def get_end_message_third_person(self, character_name: str) -> str:
        """Get the third-person message shown to others when this effect ends."""
        template = _NAMED_EFFECT_END_MESSAGES_THIRD_PERSON.get(
            self, f"{character_name} is no longer affected by {self.value}."
        )
        return template.format(name=character_name)

    # ------------------------------------------------------------------ #
    #  Registry lookups — single source of truth for effect metadata
    # ------------------------------------------------------------------ #

    @property
    def effect_condition(self):
        """The Condition enum associated with this effect, or None."""
        return _EFFECT_CONDITIONS.get(self)

    @property
    def effect_duration_type(self):
        """The default duration_type for this effect: 'combat_rounds', 'seconds', or None."""
        return _EFFECT_DURATION_TYPES.get(self)


# ================================================================== #
#  Message Registries
# ================================================================== #

_NAMED_EFFECT_START_MESSAGES = {
    NamedEffect.STUNNED: "You feel dazed and disoriented, unable to act.",
    NamedEffect.PRONE: "You fall to the ground, unable to move properly.",
    NamedEffect.SLOWED: "Your movements become sluggish and slow.",
    NamedEffect.SHIELD: "A shimmering barrier of magical force springs into existence around you!",
    NamedEffect.ARMORED: "A protective aura wraps around you.",
    NamedEffect.SHADOWCLOAKED: "Shadows coil around you, muffling your presence.",
    NamedEffect.PARALYSED: "Your muscles seize up and you cannot move!",
    NamedEffect.POISONED: "You feel poison burning through your veins!",
    NamedEffect.ACID_ARROW: "A bolt of acid sears into you, burning and corroding!",
    NamedEffect.ENTANGLED: "Weighted cords wrap around your legs, binding you in place!",
    NamedEffect.BLURRED: "Your image shimmers and distorts, making you harder to hit!",
    NamedEffect.TRUE_SIGHT: "Your eyes tingle with magical energy. The world reveals its secrets to you.",
    NamedEffect.HOLY_SIGHT: "Divine light fills your vision. The sacred reveals what is concealed.",
    NamedEffect.INVISIBLE: "Your body shimmers and fades from sight.",
    NamedEffect.OFFENSIVE_STANCE: "You shift to an aggressive fighting stance!",
    NamedEffect.DEFENSIVE_STANCE: "You shift to a defensive fighting stance!",
    NamedEffect.SUNDERED: "Your armour cracks and buckles under the blow!",
    NamedEffect.STAGGERED: "A crushing blow staggers you, throwing off your aim!",
    NamedEffect.RESIST_FIRE: "A shimmering ward of fire resistance surrounds you.",
    NamedEffect.RESIST_COLD: "A shimmering ward of cold resistance surrounds you.",
    NamedEffect.RESIST_LIGHTNING: "A shimmering ward of lightning resistance surrounds you.",
    NamedEffect.RESIST_ACID: "A shimmering ward of acid resistance surrounds you.",
    NamedEffect.RESIST_POISON: "A shimmering ward of poison resistance surrounds you.",
    NamedEffect.VAMPIRIC: "Dark energy surges through you as stolen life force bolsters your vitality!",
    NamedEffect.BRAVERY: "Divine courage fills you! You feel tougher and harder to hit.",
    NamedEffect.SANCTUARY: "A shimmering divine ward surrounds you, shielding you from harm.",
}

_NAMED_EFFECT_END_MESSAGES = {
    NamedEffect.STUNNED: "Your head clears and you shake off the dizziness.",
    NamedEffect.PRONE: "You regain your footing and stand back up.",
    NamedEffect.SLOWED: "You shake off the sluggishness and move normally again.",
    NamedEffect.SHIELD: "The shimmering barrier of force around you fades away.",
    NamedEffect.ARMORED: "The protective aura around you fades away.",
    NamedEffect.SHADOWCLOAKED: "The cloak of shadows dissipates and you feel exposed once more.",
    NamedEffect.PARALYSED: "Your muscles relax and you can move again.",
    NamedEffect.POISONED: "The poison finally runs its course.",
    NamedEffect.ACID_ARROW: "The acid finally stops burning.",
    NamedEffect.ENTANGLED: "You tear free from the tangling cords!",
    NamedEffect.BLURRED: "Your image solidifies and you become easy to see again.",
    NamedEffect.TRUE_SIGHT: "The magical sight fades and the world's secrets are hidden once more.",
    NamedEffect.HOLY_SIGHT: "The divine light fades from your vision and the world grows dim once more.",
    NamedEffect.INVISIBLE: "Your body shimmers back into view.",
    NamedEffect.OFFENSIVE_STANCE: "You return to your normal fighting stance.",
    NamedEffect.DEFENSIVE_STANCE: "You return to your normal fighting stance.",
    NamedEffect.SUNDERED: "Your armour repairs itself from the damage.",
    NamedEffect.STAGGERED: "You recover your balance and steady your aim.",
    NamedEffect.RESIST_FIRE: "Your ward of fire resistance fades.",
    NamedEffect.RESIST_COLD: "Your ward of cold resistance fades.",
    NamedEffect.RESIST_LIGHTNING: "Your ward of lightning resistance fades.",
    NamedEffect.RESIST_ACID: "Your ward of acid resistance fades.",
    NamedEffect.RESIST_POISON: "Your ward of poison resistance fades.",
    NamedEffect.VAMPIRIC: "The stolen life force drains from your body, leaving you weakened.",
    NamedEffect.BRAVERY: "The divine courage fades and you feel your normal self again.",
    NamedEffect.SANCTUARY: "The divine sanctuary around you fades.",
}

_NAMED_EFFECT_START_MESSAGES_THIRD_PERSON = {
    NamedEffect.STUNNED: "{name} staggers and looks dazed and disoriented.",
    NamedEffect.PRONE: "{name} falls to the ground, unable to move properly.",
    NamedEffect.SLOWED: "{name}'s movements become sluggish and slow.",
    NamedEffect.SHIELD: "A shimmering barrier of force springs up around {name}!",
    NamedEffect.ARMORED: "A protective aura wraps around {name}.",
    NamedEffect.SHADOWCLOAKED: "Shadows coil around {name}, muffling their presence.",
    NamedEffect.PARALYSED: "{name}'s muscles seize up and they freeze in place!",
    NamedEffect.POISONED: "{name} looks sickly as poison burns through their veins.",
    NamedEffect.ACID_ARROW: "A bolt of acid sears into {name}, burning and corroding!",
    NamedEffect.ENTANGLED: "Weighted cords wrap around {name}'s legs, binding them in place!",
    NamedEffect.BLURRED: "{name}'s image shimmers and distorts, making them harder to hit!",
    NamedEffect.TRUE_SIGHT: "{name}'s eyes begin to glow with a faint magical light.",
    NamedEffect.HOLY_SIGHT: "{name}'s eyes begin to glow with a warm divine light.",
    NamedEffect.INVISIBLE: "{name}'s body shimmers and fades from sight.",
    NamedEffect.OFFENSIVE_STANCE: "{name} shifts to an aggressive fighting stance!",
    NamedEffect.DEFENSIVE_STANCE: "{name} shifts to a defensive fighting stance!",
    NamedEffect.SUNDERED: "{name}'s armour cracks and buckles under the blow!",
    NamedEffect.STAGGERED: "{name} staggers from a crushing blow, thrown off balance!",
    NamedEffect.RESIST_FIRE: "A shimmering ward of fire resistance surrounds {name}.",
    NamedEffect.RESIST_COLD: "A shimmering ward of cold resistance surrounds {name}.",
    NamedEffect.RESIST_LIGHTNING: "A shimmering ward of lightning resistance surrounds {name}.",
    NamedEffect.RESIST_ACID: "A shimmering ward of acid resistance surrounds {name}.",
    NamedEffect.RESIST_POISON: "A shimmering ward of poison resistance surrounds {name}.",
    NamedEffect.VAMPIRIC: "{name}'s eyes glow with dark energy as stolen life surges through them!",
    NamedEffect.BRAVERY: "{name} straightens with divine courage, looking tougher and more resolute.",
    NamedEffect.SANCTUARY: "A shimmering divine ward surrounds {name}.",
}

_NAMED_EFFECT_END_MESSAGES_THIRD_PERSON = {
    NamedEffect.STUNNED: "{name} shakes their head and looks more alert.",
    NamedEffect.PRONE: "{name} regains their footing and stands back up.",
    NamedEffect.SLOWED: "{name} shakes off the sluggishness and moves normally again.",
    NamedEffect.SHIELD: "The shimmering barrier around {name} fades away.",
    NamedEffect.ARMORED: "The protective aura around {name} fades away.",
    NamedEffect.SHADOWCLOAKED: "The cloak of shadows around {name} dissipates.",
    NamedEffect.PARALYSED: "{name}'s muscles relax and they can move again.",
    NamedEffect.POISONED: "{name} looks relieved as the poison fades.",
    NamedEffect.ACID_ARROW: "The acid on {name} finally stops burning.",
    NamedEffect.ENTANGLED: "{name} tears free from the tangling cords!",
    NamedEffect.BLURRED: "{name}'s image solidifies and they become easy to see again.",
    NamedEffect.TRUE_SIGHT: "The magical glow fades from {name}'s eyes.",
    NamedEffect.HOLY_SIGHT: "The divine glow fades from {name}'s eyes.",
    NamedEffect.INVISIBLE: "{name}'s body shimmers back into view.",
    NamedEffect.OFFENSIVE_STANCE: "{name} returns to a normal fighting stance.",
    NamedEffect.DEFENSIVE_STANCE: "{name} returns to a normal fighting stance.",
    NamedEffect.SUNDERED: "{name}'s armour repairs itself from the damage.",
    NamedEffect.STAGGERED: "{name} recovers their balance.",
    NamedEffect.RESIST_FIRE: "The shimmering ward around {name} fades.",
    NamedEffect.RESIST_COLD: "The shimmering ward around {name} fades.",
    NamedEffect.RESIST_LIGHTNING: "The shimmering ward around {name} fades.",
    NamedEffect.RESIST_ACID: "The shimmering ward around {name} fades.",
    NamedEffect.RESIST_POISON: "The shimmering ward around {name} fades.",
    NamedEffect.VAMPIRIC: "The dark energy around {name} fades as the stolen life force drains away.",
    NamedEffect.BRAVERY: "The divine courage fades from {name} and they return to normal.",
    NamedEffect.SANCTUARY: "The divine sanctuary around {name} fades.",
}


# ================================================================== #
#  Effect Metadata Registries — Single Source of Truth
# ================================================================== #
#
# These dicts define the canonical condition flag and duration_type for
# each named effect. apply_named_effect() auto-fills from these when
# the caller doesn't provide explicit values.
#
# Effects NOT listed default to None (no condition / no duration_type).
# ================================================================== #

_EFFECT_CONDITIONS = {
    NamedEffect.SLOWED: Condition.SLOWED,
    NamedEffect.PARALYSED: Condition.PARALYSED,
    NamedEffect.INVISIBLE: Condition.INVISIBLE,
    NamedEffect.SANCTUARY: Condition.SANCTUARY,
}

_EFFECT_DURATION_TYPES = {
    # Combat round effects — decremented by tick_combat_round(), cleared on combat end
    NamedEffect.STUNNED: "combat_rounds",
    NamedEffect.PRONE: "combat_rounds",
    NamedEffect.SLOWED: "combat_rounds",
    NamedEffect.PARALYSED: "combat_rounds",
    NamedEffect.ENTANGLED: "combat_rounds",
    NamedEffect.BLURRED: "combat_rounds",
    NamedEffect.SHIELD: "combat_rounds",
    NamedEffect.STAGGERED: "combat_rounds",
    NamedEffect.SUNDERED: "combat_rounds",
    NamedEffect.OFFENSIVE_STANCE: "combat_rounds",
    NamedEffect.DEFENSIVE_STANCE: "combat_rounds",
    # Seconds-based effects — managed by EffectTimerScript (wall-clock)
    NamedEffect.INVISIBLE: "seconds",
    NamedEffect.BRAVERY: "seconds",
    NamedEffect.SANCTUARY: "seconds",
    NamedEffect.ARMORED: "seconds",
    NamedEffect.SHADOWCLOAKED: "seconds",
    NamedEffect.TRUE_SIGHT: "seconds",
    NamedEffect.HOLY_SIGHT: "seconds",
    NamedEffect.RESIST_FIRE: "seconds",
    NamedEffect.RESIST_COLD: "seconds",
    NamedEffect.RESIST_LIGHTNING: "seconds",
    NamedEffect.RESIST_ACID: "seconds",
    NamedEffect.RESIST_POISON: "seconds",
    NamedEffect.POTION_STRENGTH: "seconds",
    NamedEffect.POTION_DEXTERITY: "seconds",
    NamedEffect.POTION_CONSTITUTION: "seconds",
    NamedEffect.POTION_INTELLIGENCE: "seconds",
    NamedEffect.POTION_WISDOM: "seconds",
    NamedEffect.POTION_CHARISMA: "seconds",
    # Script-managed effects — lifecycle handled by custom scripts, not the effect system
    NamedEffect.POISONED: None,
    NamedEffect.ACID_ARROW: None,
    NamedEffect.VAMPIRIC: None,
}


# ================================================================== #
#  On-Apply Callbacks
# ================================================================== #
#
# Registered side effects that fire automatically when a named effect
# is applied via apply_named_effect(). Keeps mechanical side effects
# consistent regardless of source (weapon, spell, trap, command).
#
# Callbacks receive: (target, source, duration)
#   target   — the actor the effect was applied to
#   source   — the actor/object that caused the effect (may be None)
#   duration — the duration value passed to apply_named_effect
# ================================================================== #


def _grant_advantage_to_enemies(target, source, duration):
    """Grant advantage to all enemies of target for duration rounds.

    Used by: PRONE, ENTANGLED, PARALYSED — any effect where the target
    is incapacitated and attackers should have an easier time hitting.
    """
    from combat.combat_utils import get_sides
    _, enemies_of_target = get_sides(target)
    for enemy in enemies_of_target:
        handler = enemy.scripts.get("combat_handler")
        if handler:
            handler[0].set_advantage(target, duration)


def _apply_slowed(target, source, duration):
    """SLOWED on-apply callback.

    The per-round enforcement (cap attacks at 1, block off-hand, sluggish
    message) lives in combat_handler.execute_next_action() — it reads
    has_effect("slowed") each tick.  This callback is the registration
    point so SLOWED is a first-class named effect with a single source
    of truth for on-apply behaviour.
    """
    pass  # per-round mechanic enforced in combat_handler


_ON_APPLY_CALLBACKS = {
    NamedEffect.PRONE: _grant_advantage_to_enemies,
    NamedEffect.ENTANGLED: _grant_advantage_to_enemies,
    NamedEffect.PARALYSED: _grant_advantage_to_enemies,
    NamedEffect.SLOWED: _apply_slowed,
    # Effects with no mechanical side effects beyond their core behaviour:
    # STUNNED — action denial only (no advantage for enemies)
    # SHIELD — AC bonus via effects= param
    # ARMORED — AC bonus via effects= param
    # INVISIBLE — condition flag set via condition= param
    # TRUE_SIGHT — condition flag set via condition= param
    # BLURRED — script-based, managed by caller
    # POISONED — script-based, managed by caller
    # ACID_ARROW — script-based, managed by caller
    # POTION_* — stat bonus via effects= param
}


def get_on_apply_callback(key):
    """Look up the on-apply callback for a named effect key string."""
    try:
        ne = NamedEffect(key)
    except ValueError:
        return None
    return _ON_APPLY_CALLBACKS.get(ne)


# ================================================================== #
#  UNSORTED EFFECTS — must be classified before implementation
# ================================================================== #
#
# These effects have NOT been examined yet. When implementing any of
# them, you MUST classify them as:
#   - NamedEffect (lifecycle-managed via apply_named_effect)
#   - Condition (ref-counted flag checked via has_condition)
#   - Both (like SLOWED — named effect for lifecycle + condition flag for checks)
#
# Add them to the appropriate enum(s) and remove from this list.
# Do NOT implement an effect that is still in this unsorted list.
#
# ---- Sense Restrictions ----
# BLIND          — CLASSIFIED → Condition.BLINDED (condition.py)
# DEAF           — CLASSIFIED → Condition.DEAF (condition.py)
#
# ---- Movement / Action Restrictions ----
# PETRIFIED      — turned to stone, total incapacitation
#
# ---- Ability / Spell Effects ----
# CHARMED        — can't attack the mob that charmed them
# SLEEP          — put to sleep by spell, wake on damage
# BLESSED        — extra d4 on attack rolls
# FRENZIED       — increasing damage resistances + extra damage per attack (mastery-scaled)
# CURSED         — negative penalty on all rolls
# ALERT          — bonus to initiative rolls
#
# ---- Abjuration Spell Effects ----
# SHIELDED       — (REPLACED by NamedEffect.SHIELD — kept here for reference only)
# ANTIMAGIC      — antimagic field active, no casting, dispels active effects
# INVULNERABLE   — total damage/condition immunity (1 round, grandmaster)
#
# ---- Necromancy Spell Effects ----
# DEATH_MARKED   — all damage heals the attacker (grandmaster necromancy)
#
# ---- Conjuration Spell Effects ----
# DIMENSION_LOCKED — no flee/teleport/summon (Dimensional Lock spell)
#
# ---- Illusion Spell Effects ----
# CONFUSED       — random target selection in combat (Mass Confusion)
