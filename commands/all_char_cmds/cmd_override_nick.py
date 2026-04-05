import re

from evennia.commands.default.general import CmdNick as _CmdNick

from commands.command import FCMCommandMixin


class CmdNick(FCMCommandMixin, _CmdNick):
    """
    Define a personal alias.

    Usage:
        alias <name> <command(s)>        — create alias (semicolons for multi-command)
        alias <name> = <command(s)>      — also works with =
        alias/list                       — show all aliases
        alias/delete <name or number>    — remove an alias

    Examples:
        alias dc get canteen bag;drink canteen;put canteen bag
        alias dc = get canteen bag;drink canteen;put canteen bag
        alias mm cast magic missile
        alias heal cast cure wounds $1
    """

    help_category = "System"
    aliases = ["alias"]

    def parse(self):
        """Support 'alias name replacement' without requiring =."""
        super().parse()
        # If parent parse found no rhs (no = sign), treat the first word
        # as the alias name and the rest as the replacement.
        if self.rhs is None and self.lhs and not self.switches:
            parts = self.lhs.split(None, 1)
            if len(parts) == 2:
                self.lhs, self.rhs = parts
