from evennia.commands.default.general import CmdPose as _CmdPose

from commands.command import FCMCommandMixin


class CmdPose(FCMCommandMixin, _CmdPose):
    """
    Strike a pose.

    Usage:
        pose <pose text>
        pose's <pose text>

    Example:
        pose is standing by the wall, smiling.
         -> others will see:
        Tom is standing by the wall, smiling.

    Describe an action being taken. The pose text will
    automatically begin with your name.
    """

    help_category = "Communication"
