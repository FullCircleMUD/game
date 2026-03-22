"""
Condition flags — ref-counted boolean flags checked via has_condition().

These are persistent state flags on an actor, managed by the EffectsManagerMixin
Layer 1 (add_condition / remove_condition / has_condition). They are ref-counted:
multiple sources can add the same condition, and the flag only clears when all
sources have removed it.

For named effects (lifecycle-managed via apply_named_effect), see enums/named_effect.py.
Some effects appear in BOTH systems — e.g. SLOWED is a named effect for lifecycle
management AND a condition flag checked via has_condition() for movement speed.

For unclassified effects that need examination before implementation, see the
UNSORTED EFFECTS comment block at the bottom of enums/named_effect.py.
"""

from enum import Enum


class Condition(Enum):
    #########################################################
    # Sense Restrictions
    #########################################################
    # USED: cmd_say.py (has_condition check prevents speech)
    SILENCED = "silenced"  # unable to speak
    # USED: cmd_say.py, cmd_whisper.py, cmd_shout.py (deaf listeners hear nothing)
    DEAF = "deaf"  # unable to hear speech

    #########################################################
    # Stealth / Stealth Detection
    #########################################################
    # USED: cmd_hide.py (applied), cmd_search.py / cmd_attack.py (removed),
    #   room_base.py / base_actor.py / character.py (visibility filtering)
    HIDDEN = "hidden"
    # USED: base_actor.py / room_base.py / cmd_say.py (visibility filtering checks),
    #   no command/spell applies it yet — test-only application
    INVISIBLE = "invisible"
    # USED: room_base.py / invisible_object.py / cmd_say.py (see-invis checks),
    #   no command/spell applies it yet — test-only application
    DETECT_INVIS = "detect_invis"

    #########################################################
    # Racial / Environmental Abilities
    #########################################################
    # USED: test-only application — no command/spell applies it yet
    # Will be applied by racial traits system when implemented
    DARKVISION = "darkvision"  # can see after dark without a light
    # USED: cmd_fly.py (requires FLY), base_actor.py (fall damage on removal)
    FLY = "fly"               # can fly / move through air rooms
    # USED: cmd_swim.py (requires for underwater), breath_timer.py (bypasses drowning),
    #   base_actor.py (starts/stops breath timer on gain/loss)
    WATER_BREATHING = "water_breathing"  # can breathe underwater

    #########################################################
    # Ability / Spell Effects
    #########################################################
    # USED: conditions.py mixin (ref-counted application), effective_attacks_per_round
    HASTED = "hasted"  # extra attack per round
    # USED: cmd_say.py (has_condition check enables language comprehension),
    #   no command/spell applies it yet — test-only application
    COMPREHEND_LANGUAGES = "comprehend_languages"  # understand all spoken languages
    # USED: combat_utils.py (downgrades crit to normal hit),
    #   no command/spell applies it yet — test-only application
    CRIT_IMMUNE = "crit_immune"
    # USED: sanctuary spell (divine protection), combat_utils (target protection),
    #   cmd_cast.py (breaks on offensive cast), break_sanctuary() on attack
    SANCTUARY = "sanctuary"  # enemies cannot target this actor

    #########################################################
    # Dual-system (also a NamedEffect — see named_effect.py)
    #########################################################
    # NAMED EFFECT: applied by blowgun_nft_item.py (at_hit) as named effect with condition flag
    # Condition flag for Remove Paralysis spell targeting (has_condition check).
    # Lifecycle managed by NamedEffect.PARALYSED — do NOT manage duration via conditions.
    # See enums/named_effect.py for lifecycle details.
    PARALYSED = "paralyzed"  # unable to move or act (stronger than stun)
    # NAMED EFFECT: applied by cone_of_cold.py as named effect with condition flag
    # Condition flag set for future movement speed system (has_condition check).
    # Lifecycle managed by NamedEffect.SLOWED — do NOT manage duration via conditions.
    # See enums/named_effect.py for lifecycle details.
    SLOWED = "slowed"  # movement speed reduced

    # ------------------------------------------------------------------ #
    #  Message methods
    # ------------------------------------------------------------------ #

    def get_start_message(self) -> str:
        """Get the first-person message shown when this condition begins."""
        return _CONDITION_START_MESSAGES.get(self, f"You are now affected by {self.value}.")

    def get_end_message(self) -> str:
        """Get the first-person message shown when this condition ends."""
        return _CONDITION_END_MESSAGES.get(self, f"You are no longer affected by {self.value}.")

    def get_start_message_third_person(self, character_name: str) -> str:
        """Get the third-person message shown to others when this condition begins."""
        template = _CONDITION_START_MESSAGES_THIRD_PERSON.get(self, f"{character_name} is now affected by {self.value}.")
        return template.format(name=character_name)

    def get_end_message_third_person(self, character_name: str) -> str:
        """Get the third-person message shown to others when this condition ends."""
        template = _CONDITION_END_MESSAGES_THIRD_PERSON.get(self, f"{character_name} is no longer affected by {self.value}.")
        return template.format(name=character_name)


# ================================================================== #
#  Message Registries
# ================================================================== #

_CONDITION_START_MESSAGES = {
    # Sense Restrictions
    Condition.SILENCED: "Your throat constricts and you find yourself unable to speak.",
    Condition.DEAF: "Your ears fill with a deadening silence.",

    # Stealth / Stealth Detection
    Condition.HIDDEN: "You blend into the shadows, becoming difficult to spot.",
    Condition.INVISIBLE: "Your body shimmers and fades from sight.",
    Condition.DETECT_INVIS: "Your eyes tingle with magical energy. You can now see invisible things.",

    # Racial / Environmental Abilities
    Condition.FLY: "Your feet lift off the ground and you begin to fly.",
    Condition.WATER_BREATHING: "Your lungs tingle as you gain the ability to breathe underwater.",

    # Ability / Spell Effects
    Condition.HASTED: "You start moving much faster than usual.",
    Condition.COMPREHEND_LANGUAGES: "You feel a surge of understanding. All languages become clear.",
    Condition.SANCTUARY: "A shimmering divine ward surrounds you, shielding you from harm.",

    # Dual-system
    Condition.PARALYSED: "Your muscles seize up and you cannot move!",
    Condition.SLOWED: "Your movements become sluggish and slow.",
}

_CONDITION_END_MESSAGES = {
    # Sense Restrictions
    Condition.SILENCED: "Your throat relaxes and you can speak again.",
    Condition.DEAF: "Your hearing gradually returns.",

    # Stealth / Stealth Detection
    Condition.HIDDEN: "You step out of the shadows, becoming visible again.",
    Condition.INVISIBLE: "Your body shimmers back into view.",
    Condition.DETECT_INVIS: "The magical sight fades and your eyes return to normal.",

    # Racial / Environmental Abilities
    Condition.FLY: "You drift back to the ground as the power of flight leaves you.",
    Condition.WATER_BREATHING: "Your lungs return to normal. You can no longer breathe underwater.",

    # Ability / Spell Effects
    Condition.HASTED: "You slow back down to normal speed.",
    Condition.COMPREHEND_LANGUAGES: "The magical translation fades from your mind.",
    Condition.SANCTUARY: "The divine sanctuary around you fades.",

    # Dual-system
    Condition.PARALYSED: "Your muscles relax and you can move again.",
    Condition.SLOWED: "You shake off the sluggishness and move normally again.",
}

_CONDITION_START_MESSAGES_THIRD_PERSON = {
    # Sense Restrictions
    Condition.SILENCED: "{name} opens their mouth but no sound comes out.",
    Condition.DEAF: "{name} claps their hands over their ears as sound fades away.",

    # Stealth / Stealth Detection
    Condition.HIDDEN: "{name} melts into the shadows and becomes hard to spot.",
    Condition.INVISIBLE: "{name}'s body shimmers and fades from sight.",
    Condition.DETECT_INVIS: "{name}'s eyes begin to glow with a faint magical light.",

    # Racial / Environmental Abilities
    Condition.FLY: "{name}'s feet lift off the ground as they begin to fly.",
    Condition.WATER_BREATHING: "{name}'s breathing changes as they gain the ability to breathe underwater.",

    # Ability / Spell Effects
    Condition.HASTED: "{name} starts moving much faster than usual.",
    Condition.COMPREHEND_LANGUAGES: "{name}'s eyes widen with sudden understanding.",
    Condition.SANCTUARY: "A shimmering divine ward surrounds {name}.",

    # Dual-system
    Condition.PARALYSED: "{name}'s muscles seize up and they freeze in place!",
    Condition.SLOWED: "{name}'s movements become sluggish and slow.",
}

_CONDITION_END_MESSAGES_THIRD_PERSON = {
    # Sense Restrictions
    Condition.SILENCED: "{name} clears their throat and can speak again.",
    Condition.DEAF: "{name}'s expression eases as their hearing returns.",

    # Stealth / Stealth Detection
    Condition.HIDDEN: "{name} steps out of the shadows and becomes visible again.",
    Condition.INVISIBLE: "{name}'s body shimmers back into view.",
    Condition.DETECT_INVIS: "The magical glow fades from {name}'s eyes.",

    # Racial / Environmental Abilities
    Condition.FLY: "{name} drifts back to the ground as the power of flight fades.",
    Condition.WATER_BREATHING: "{name}'s breathing returns to normal.",

    # Ability / Spell Effects
    Condition.HASTED: "{name} slows back down to normal speed.",
    Condition.COMPREHEND_LANGUAGES: "The look of deep understanding fades from {name}'s eyes.",
    Condition.SANCTUARY: "The divine sanctuary around {name} fades.",

    # Dual-system
    Condition.PARALYSED: "{name}'s muscles relax and they can move again.",
    Condition.SLOWED: "{name} shakes off the sluggishness and moves normally again.",
}
