from evennia.commands.default.general import CmdSetDesc as _CmdSetDesc

from commands.command import FCMCommandMixin


class CmdSetDesc(FCMCommandMixin, _CmdSetDesc):
    help_category = "Character"
