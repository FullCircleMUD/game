"""
Follow / Unfollow / Nofollow commands for group formation.

Players form groups by following a leader. Chain resolution ensures
that following someone who already follows someone else resolves to
the chain leader: A follows B follows C → A's leader is C.

When the leader moves through an exit, all followers in the same
room auto-move via FCMCharacter.at_post_move().
"""

from evennia import Command


class CmdFollow(Command):
    """
    Follow another character, forming or joining a group.

    Usage:
        follow <character>

    Following someone who is already following another character
    makes you follow their leader instead. When the leader moves,
    you move automatically.
    """

    key = "follow"
    aliases = ("fol", "foll")
    locks = "cmd:all()"
    help_category = "Group"

    def func(self):
        caller = self.caller

        if not self.args.strip():
            # Show current follow status
            if caller.following:
                leader = caller.get_group_leader()
                if leader == caller.following:
                    caller.msg(f"You are following {caller.following.key}.")
                else:
                    caller.msg(
                        f"You are following {caller.following.key} "
                        f"(group leader: {leader.key})."
                    )
            else:
                caller.msg("You are not following anyone.")
            return

        target = caller.search(self.args.strip())
        if not target:
            return

        # Can't follow yourself
        if target == caller:
            caller.msg("You can't follow yourself.")
            return

        # Can't follow non-characters (must have follow system)
        if not hasattr(target, "following"):
            caller.msg("You can only follow other characters.")
            return

        # Must be in the same room
        if target.location != caller.location:
            caller.msg("They aren't here.")
            return

        # Resolve to the chain leader
        leader = target.get_group_leader()

        # Check nofollow on the resolved leader
        if leader.nofollow:
            caller.msg(f"{leader.key} is not accepting followers.")
            return

        # Check nofollow on the direct target (if different from leader)
        if target != leader and target.nofollow:
            caller.msg(f"{target.key} is not accepting followers.")
            return

        # Already following this target's leader?
        if caller.following:
            current_leader = caller.get_group_leader()
            if current_leader == leader:
                caller.msg(f"You are already in {leader.key}'s group.")
                return

        # Would this create a cycle? (target already follows caller)
        if target.get_group_leader() == caller:
            caller.msg(
                f"{target.key} is already following you. "
                f"They would need to unfollow first."
            )
            return

        # Set follow — always follow the direct target, not the resolved leader.
        # Chain resolution handles the rest.
        caller.following = target
        caller.msg(f"You start following {target.key}.")
        target.msg(f"{caller.key} starts following you.")
        caller.location.msg_contents(
            f"$You() $conj(start) following {target.key}.",
            from_obj=caller,
            exclude=[caller, target],
        )


class CmdUnfollow(Command):
    """
    Stop following your current leader.

    Usage:
        unfollow
    """

    key = "unfollow"
    aliases = ("unf", "unfo", "unfol")
    locks = "cmd:all()"
    help_category = "Group"

    def func(self):
        caller = self.caller

        if not caller.following:
            caller.msg("You are not following anyone.")
            return

        target = caller.following
        caller.following = None
        caller.msg(f"You stop following {target.key}.")
        if target.location == caller.location:
            target.msg(f"{caller.key} stops following you.")
            caller.location.msg_contents(
                f"$You() $conj(stop) following {target.key}.",
                from_obj=caller,
                exclude=[caller, target],
            )


class CmdNofollow(Command):
    """
    Toggle whether other characters can follow you.

    Usage:
        nofollow                - toggle (when no followers)
        nofollow keep           - block new followers, keep current group
        nofollow disband        - block new followers, disband group

    When nofollow is on, other characters cannot follow you.
    If you have followers, you must specify 'keep' or 'disband'.

    This is a convenience alias for 'toggle nofollow'.
    """

    key = "nofollow"
    aliases = ["nof", "nofol"]
    locks = "cmd:all()"
    help_category = "Group"

    def func(self):
        from commands.all_char_cmds.cmd_toggle import _handle_nofollow_toggle
        _handle_nofollow_toggle(self.caller, self.args.strip())


class CmdGroup(Command):
    """
    See who is in your group.

    Usage:
        group
    """

    key = "group"
    locks = "cmd:all()"
    help_category = "Group"

    def func(self):
        caller = self.caller

        leader = caller.get_group_leader()
        followers = leader.get_followers(same_room=False)

        if not followers and leader == caller:
            caller.msg("You are not in a group.")
            return

        lines = [f"|wGroup leader:|n {leader.key}"]
        for f in followers:
            loc = ""
            if f.location != caller.location:
                loc = f" |x(elsewhere)|n"
            lines.append(f"  {f.key}{loc}")

        caller.msg("\n".join(lines))
