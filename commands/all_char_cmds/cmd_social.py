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

from commands.command import FCMCommandMixin
from enums.condition import Condition
from commands.all_char_cmds.socials_data import SOCIALS
from utils.targeting.helpers import walk_contents
from utils.targeting.predicates import p_can_see


class CmdSocialBase(FCMCommandMixin, Command):
    """
    Base class for all social commands.

    Not used directly — subclasses are generated dynamically by
    _make_social_cmd() from SOCIALS data.
    """

    locks = "cmd:all()"
    help_category = "Socials"
    social_data = None  # set by factory

    #: Whether this social makes no sound. Silent socials are purely
    #: visual — an observer who can't see the actor perceives nothing at
    #: all. Non-silent socials (fart, whistle, cackle) still reach them,
    #: with the actor's name replaced by "Someone".
    #:
    #: Defaults True, so a social only declares ``"silent": False`` in
    #: SOCIALS when it is audible.
    silent = True

    def _break_hiding(self, caller):
        """Interacting with the room gives up physical concealment.

        Socials exist to engage the people around you, and engaging with
        the room is incompatible with hiding from it. That holds whether
        or not anyone perceived the social — the act of interacting is
        what costs you the hiding place, not being noticed doing it.

        Magical invisibility is unaffected: it doesn't depend on staying
        still or out of sight.

        Called only once the social is certain to happen — a mistyped or
        unresolvable target must not cost the actor their concealment.
        """
        if hasattr(caller, "has_condition") and caller.has_condition(
            Condition.HIDDEN
        ):
            caller.remove_condition(Condition.HIDDEN)

    def _send_to_room(self, caller, room_msg, exclude, mapping=None):
        """Broadcast the room line, respecting what observers can perceive.

        A silent social is purely visual, so ``msg_contents`` dropping
        everyone who can't see the actor is the whole answer.

        A non-silent one still reaches them — they hear the laugh, or see
        the target flinch. The same template is passed as both arguments
        because ``get_display_name`` renders the actor as "Someone" for
        anyone who can't see them, so the anonymised line conjugates
        itself.

        ``mapping`` carries the target through to ``msg_contents``, which
        resolves it per recipient via ``get_display_name``. The target
        must NOT be pre-substituted into the string — that would name a
        concealed target to the whole room off the caller's view of them.
        """
        if not caller.location:
            return
        if self.silent:
            caller.location.msg_contents(
                room_msg, from_obj=caller, exclude=exclude, mapping=mapping
            )
        else:
            caller.location.msg_contents_with_invis_alt(
                room_msg, room_msg, from_obj=caller, exclude=exclude,
                mapping=mapping,
            )

    def func(self):
        caller = self.caller
        data = self.social_data
        if not data:
            caller.msg("Something went wrong with that social.")
            return

        # Concealment does not stop you acting — it stops others perceiving
        # you. HIDDEN and INVISIBLE are both handled downstream, in
        # _send_to_room and the victim message, on the same rule: what an
        # observer receives depends on whether they can see you, never on
        # why they can't.
        args = self.args.strip() if self.args else ""

        # ── No target ──
        if not args:
            self_msg = data.get("no_target_self")
            room_msg = data.get("no_target_room")
            # Committed — nothing left that can fail.
            self._break_hiding(caller)
            if self_msg:
                caller.msg(self_msg)
            if room_msg:
                self._send_to_room(caller, room_msg, exclude=[caller])
            return

        # ── Find target ──
        # Only what the caller can perceive is targetable. The caller is
        # always a candidate — p_can_see would reject their own concealed
        # self, and "bow self" must keep working while invisible.
        candidates = walk_contents(caller, caller.location, p_can_see)
        if caller not in candidates:
            candidates.append(caller)
        target = caller.search(args, candidates=candidates)
        if not target:
            return

        # Target resolved — the social will happen, so concealment goes.
        self._break_hiding(caller)

        # ── Self-target ──
        if target == caller:
            self_msg = data.get("self_self")
            room_msg = data.get("self_room")
            if self_msg:
                caller.msg(self_msg)
            elif data.get("no_target_self"):
                caller.msg(data["no_target_self"])
            if room_msg:
                self._send_to_room(caller, room_msg, exclude=[caller])
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
            # The target is told who did it only if they can see the actor.
            # A silent social they can't see never happened as far as they
            # are concerned; an audible one still reaches them, unattributed.
            if p_can_see(caller, target):
                target.msg(victim_msg.format(actor=actor_name, target=target_name))
            elif not self.silent:
                target.msg(victim_msg.format(actor="Someone", target=target_name))

        if room_msg:
            # {target} is left in the template and resolved per recipient
            # by msg_contents, so a concealed target reads as "Someone" to
            # anyone who can't see them.
            self._send_to_room(
                caller, room_msg, exclude=[caller, target],
                mapping={"target": target},
            )


def _make_social_cmd(name, data):
    """Factory: create a Command subclass for one social."""
    aliases = data.get("aliases", [])
    no_target_msg = data.get("no_target_self", f"You {name}.")

    class _Cmd(CmdSocialBase):
        key = name
        social_data = data
        silent = data.get("silent", True)

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


class CmdSocials(FCMCommandMixin, Command):
    """
    List all available social commands.

    Usage:
        socials

    Shows all social commands you can use to express yourself.
    """

    key = "socials"
    locks = "cmd:all()"
    help_category = "Socials"
    allow_while_sleeping = True

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
