"""
Toggle command — view and flip player preferences.

Reads available preferences from ``PlayerPreferencesMixin.PREFERENCES``
so adding new toggles requires no command changes.  Gated preferences
(e.g. reactive spells) are checked before toggling.

Nofollow has special handling: when a group leader turns nofollow ON,
they must specify ``keep`` (keep followers) or ``disband`` (kick them).
"""

from evennia import Command

from commands.command import FCMCommandMixin


def _handle_nofollow_toggle(caller, modifier):
    """Shared logic for toggling nofollow, used by CmdToggle and CmdNofollow.

    Returns True if the toggle was handled (caller already messaged).
    Returns False if this isn't a nofollow situation (let normal toggle proceed).
    """
    # Only intervene when turning nofollow ON while leading a group
    if caller.nofollow:
        # Turning OFF — simple toggle, no modifier needed
        caller.toggle_preference("nofollow")
        caller.msg("nofollow is now |rOFF|n. Others can follow you again.")
        return True

    # Turning ON — check for followers
    followers = caller.get_followers(same_room=False)
    if not followers:
        # No followers — simple toggle
        caller.toggle_preference("nofollow")
        caller.msg("nofollow is now |gON|n. Others cannot follow you.")
        return True

    # Has followers — require keep/disband
    mod = modifier.lower().strip() if modifier else ""

    if mod == "keep":
        caller.toggle_preference("nofollow")
        caller.msg(
            "nofollow is now |gON|n. Current followers remain, "
            "but no new followers can join."
        )
        return True

    if mod == "disband":
        caller.toggle_preference("nofollow")
        for f in followers:
            f.following = None
            f.msg(f"{caller.key} is no longer accepting followers.")
        caller.msg(
            "nofollow is now |gON|n. Your group has been disbanded."
        )
        return True

    # No valid modifier — tell them to choose
    caller.msg(
        "You have followers. Use |wnofollow keep|n to block new "
        "followers, or |wnofollow disband|n to also disband your group."
    )
    return True


class CmdToggle(FCMCommandMixin, Command):
    """
    View or change your preferences.

    Usage:
        toggle                      - show all preferences
        toggle <preference>         - flip a preference on/off
        toggle nofollow keep        - block followers, keep current group
        toggle nofollow disband     - block followers, disband group

    Examples:
        toggle
        toggle brief
        toggle autoexit
        toggle smite
        toggle nofollow disband
    """

    key = "toggle"
    locks = "cmd:all()"
    help_category = "System"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller

        if not hasattr(caller, "PREFERENCES"):
            caller.msg("You have no configurable preferences.")
            return

        if not self.args:
            caller.msg(caller.get_preference_display())
            return

        # Split into preference name + optional modifier
        parts = self.args.strip().split(None, 1)
        pref_name = parts[0]
        modifier = parts[1] if len(parts) > 1 else ""

        # Nofollow has special keep/disband handling
        if pref_name.lower() == "nofollow":
            _handle_nofollow_toggle(caller, modifier)
            return

        # Modifiers not supported for other preferences
        if modifier:
            pref_name = self.args.strip()

        result = caller.toggle_preference(pref_name)
        if result is None:
            # Unknown preference — only show options the player can access
            valid = [
                name for name, entry in caller.PREFERENCES.items()
                if caller._passes_gate(entry)
            ]
            caller.msg(
                f"Unknown preference '{pref_name}'. "
                f"Valid options: {', '.join(valid)}"
            )
            return

        name, new_val = result
        if name is None:
            # Gate failure — new_val is the error message
            caller.msg(new_val)
            return

        status = "|gON|n" if new_val else "|rOFF|n"
        caller.msg(f"{name} is now {status}.")
