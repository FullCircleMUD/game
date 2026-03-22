"""
CmdSetSocials — dynamically generated social commands from SOCIALS registry.

Loaded as a sub-CmdSet inside CmdSetCharacterCustom. Each social in
socials_data.SOCIALS becomes a real Command subclass with its own key,
aliases, and help entry.
"""

from evennia import CmdSet

from commands.all_char_cmds.cmd_social import create_social_commands, CmdSocials


class CmdSetSocials(CmdSet):
    key = "CmdSetSocials"

    def at_cmdset_creation(self):
        for cmd_cls in create_social_commands():
            self.add(cmd_cls())
        self.add(CmdSocials())
