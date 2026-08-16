from django.conf import settings

from utils.targeting.predicates import p_is_character


def award_skill_xp(caller, amount, target=None):
    if not getattr(settings, "SKILL_XP_ENABLED", True):
        return
    if amount <= 0:
        return
    # No XP for practising on other players — that is the farming
    # exploit this exists to close.
    if target is not None and p_is_character(target, caller):
        return
    caller.at_gain_experience_points(amount)
