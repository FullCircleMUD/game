from evennia.commands.default.general import CmdPose as _CmdPose

from commands.command import FCMCommandMixin


class CmdPose(FCMCommandMixin, _CmdPose):
    help_category = "Communication"
