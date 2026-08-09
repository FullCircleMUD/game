from evennia.commands.default.general import CmdSetDesc as _CmdSetDesc

from commands.command import FCMCommandMixin


class CmdSetDesc(FCMCommandMixin, _CmdSetDesc):
    """
    Describe yourself.

    Usage:
        setdesc <description>

    Add a description to yourself. This will be visible to people
    when they look at you.
    """

    help_category = "Character"
