"""
Override of Evennia's default CmdHelp to disable the EvMore pager.

EvMore injects temporary `next`/`n`/`previous` commands into the caller's
cmdset for pagination. IC (while puppeting a character), `n` conflicts with
the `north` movement command and causes "More than one match for 'next'"
errors when two EvMore sessions overlap.

Fix: set help_more = False so help output is sent directly via self.msg()
rather than through EvMore.
"""

from evennia.commands.default.help import CmdHelp as _CmdHelp

from commands.command import FCMCommandMixin


class CmdHelp(FCMCommandMixin, _CmdHelp):
    help_more = False
