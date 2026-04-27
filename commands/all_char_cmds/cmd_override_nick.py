from evennia.commands.default.general import CmdNick as _CmdNick

from commands.command import FCMCommandMixin


class CmdNick(FCMCommandMixin, _CmdNick):
    """
    Define a personal alias.

    Usage:
        alias <name> = <command(s)>      — create alias (semicolons for multi-command)
        alias/list                       — show all aliases
        alias/delete <name or number>    — remove an alias

    Examples:
        alias dc = get canteen bag;drink canteen;put canteen bag
        alias mm = cast magic missile
        alias heal = cast cure wounds $1
    """

    help_category = "System"
    aliases = ["alias"]
    allow_while_sleeping = True
