"""
Group tell — send a message to all members of your group.

If not in a group, sends a humorous message about talking to yourself.

Usage:
    gtell <message>
    gt <message>
"""

from evennia import Command


class CmdGtell(Command):
    """
    Send a message to your group.

    Usage:
        gtell <message>
        gt <message>

    Sends a message to all members of your group, regardless of
    where they are. If you're not in a group, you'll just be
    talking to yourself.
    """

    key = "gtell"
    aliases = ["gt"]
    locks = "cmd:all()"
    help_category = "Communication"

    def func(self):
        caller = self.caller

        if not self.args.strip():
            caller.msg("Tell your group what?")
            return

        message = self.args.strip()

        leader = caller.get_group_leader()
        followers = leader.get_followers(same_room=False)

        # Build full group list (leader + all followers)
        group = [leader] + followers

        # Not in a group — just the caller alone
        if len(group) <= 1:
            caller.msg(f'|cYou tell yourself:|n "{message}"')
            if caller.location:
                caller.location.msg_contents(
                    f"{caller.key} mutters something to themselves.",
                    exclude=[caller],
                )
            return

        # Send to all group members
        for member in group:
            if member == caller:
                member.msg(f'|c[Group] You tell the group:|n "{message}"')
            else:
                member.msg(f'|c[Group] {caller.key} tells the group:|n "{message}"')
