"""
Social commands — data-driven expressive verbs (bow, shrug, laugh, etc.).

CircleMUD-style socials: each social is a first-class command generated
from the SOCIALS registry in socials_data.py. Supports no-target, targeted,
and self-target variants with multi-perspective messaging.

Dynamic class generation: _make_social_cmd() creates a unique Command
subclass per social so Evennia's command resolution and help system work
natively.
"""

from evennia import Command

from enums.condition import Condition
from commands.all_char_cmds.socials_data import SOCIALS


class CmdSocialBase(Command):
    """
    Base class for all social commands.

    Not used directly — subclasses are generated dynamically by
    _make_social_cmd() from SOCIALS data.
    """

    locks = "cmd:all()"
    help_category = "Socials"
    social_data = None  # set by factory

    def func(self):
        caller = self.caller
        data = self.social_data
        if not data:
            caller.msg("Something went wrong with that social.")
            return

        # ── Guards ──
        if caller.position == "sleeping":
            caller.msg("You can't do that while asleep.")
            return

        if hasattr(caller, "has_condition") and caller.has_condition(
            Condition.HIDDEN
        ):
            caller.msg("You can't do that while hidden.")
            return

        args = self.args.strip() if self.args else ""

        # ── No target ──
        if not args:
            self_msg = data.get("no_target_self")
            room_msg = data.get("no_target_room")
            if self_msg:
                caller.msg(self_msg)
            if room_msg and caller.location:
                caller.location.msg_contents(
                    room_msg, from_obj=caller, exclude=[caller]
                )
            return

        # ── Find target ──
        target = caller.search(args)
        if not target:
            return

        # ── Self-target ──
        if target == caller:
            self_msg = data.get("self_self")
            room_msg = data.get("self_room")
            if self_msg:
                caller.msg(self_msg)
            elif data.get("no_target_self"):
                caller.msg(data["no_target_self"])
            if room_msg and caller.location:
                caller.location.msg_contents(
                    room_msg, from_obj=caller, exclude=[caller]
                )
            return

        # ── Targeted ──
        actor_name = caller.key
        target_name = target.get_display_name(caller) if hasattr(
            target, "get_display_name"
        ) else target.key

        self_msg = data.get("target_self")
        room_msg = data.get("target_room")
        victim_msg = data.get("target_victim")

        if self_msg:
            caller.msg(self_msg.format(actor=actor_name, target=target_name))

        if victim_msg and hasattr(target, "msg"):
            target.msg(victim_msg.format(actor=actor_name, target=target_name))

        if room_msg and caller.location:
            # Room message uses $You()/$conj() — substitute {target} with
            # the target's display name for the room.
            formatted_room = room_msg.replace("{target}", target_name)
            caller.location.msg_contents(
                formatted_room,
                from_obj=caller,
                exclude=[caller, target],
            )


def _make_social_cmd(name, data):
    """Factory: create a Command subclass for one social."""
    aliases = data.get("aliases", [])
    no_target_msg = data.get("no_target_self", f"You {name}.")

    class _Cmd(CmdSocialBase):
        key = name
        social_data = data

    _Cmd.aliases = aliases
    _Cmd.__name__ = f"CmdSocial_{name.title()}"
    _Cmd.__qualname__ = _Cmd.__name__
    _Cmd.__doc__ = (
        f"{no_target_msg}\n\n"
        f"Usage:\n"
        f"    {name} [target]\n\n"
        f"A social command. Use with a target's name to direct it at them."
    )
    return _Cmd


def create_social_commands():
    """Generate Command classes for all socials in the registry."""
    return [_make_social_cmd(name, data) for name, data in SOCIALS.items()]


class CmdSocials(Command):
    """
    List all available social commands.

    Usage:
        socials

    Shows all social commands you can use to express yourself.
    """

    key = "socials"
    locks = "cmd:all()"
    help_category = "Socials"

    def func(self):
        names = sorted(SOCIALS.keys())
        if not names:
            self.caller.msg("No socials available.")
            return

        # Format in columns
        cols = 5
        rows = []
        for i in range(0, len(names), cols):
            row = "  ".join(f"{n:<14}" for n in names[i : i + cols])
            rows.append(row)

        header = f"|wAvailable socials ({len(names)}):|n"
        self.caller.msg(f"{header}\n" + "\n".join(rows))
