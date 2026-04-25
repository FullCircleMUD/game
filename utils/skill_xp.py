from django.conf import settings


def award_skill_xp(caller, amount, target=None):
    if not getattr(settings, "SKILL_XP_ENABLED", True):
        return
    if amount <= 0:
        return
    if target is not None and getattr(target, "is_pc", False):
        return
    caller.at_gain_experience_points(amount)
