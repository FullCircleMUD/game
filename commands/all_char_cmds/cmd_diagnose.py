from evennia import Command


def _health_description(current, maximum):
    """Return a descriptive string for HP percentage."""
    if maximum <= 0:
        return "|xin an unknown state|n"
    if current <= 0:
        return "|Rincapacitated|n"
    ratio = current / maximum
    if ratio >= 1.0:
        return "|gin excellent condition|n"
    elif ratio >= 0.9:
        return "|ghas a few scratches|n"
    elif ratio >= 0.75:
        return "|ghas some small wounds and bruises|n"
    elif ratio >= 0.50:
        return "|yhas quite a few wounds|n"
    elif ratio >= 0.30:
        return "|yhas some big nasty wounds and scratches|n"
    elif ratio >= 0.15:
        return "|rlooks pretty hurt|n"
    else:
        return "|ris in awful condition|n"


class CmdDiagnose(Command):
    """
    Assess the health of a character or creature.

    Usage:
        diagnose <target>
        diagnose

    Without arguments, diagnoses yourself.
    """

    key = "diagnose"
    aliases = ["diag"]
    help_category = "General"
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if not self.args or not self.args.strip():
            target = caller
        else:
            target = caller.search(self.args.strip())
            if not target:
                return

        if not hasattr(target, "hp"):
            caller.msg("You can't diagnose that.")
            return

        hp = target.hp
        hp_max = target.effective_hp_max
        desc = _health_description(hp, hp_max)

        if target == caller:
            caller.msg(f"You are {desc}. ({hp}/{hp_max} HP)")
        else:
            caller.msg(f"{target.key} {desc}. ({hp}/{hp_max} HP)")
