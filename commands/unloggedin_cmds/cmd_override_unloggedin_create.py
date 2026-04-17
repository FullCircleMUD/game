"""
Legacy create command — redirects to connect.

The create command has been merged into the connect command.
This stub remains so players who type 'create' get a helpful message.
"""

from django.conf import settings
from evennia.utils import utils

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)


class CmdUnconnectedCreate(COMMAND_DEFAULT_CLASS):
    """
    Account creation is handled by the connect command.

    Usage (at login screen):
      connect

    Just type 'connect' and sign in with your wallet. If you don't
    have an account yet, one will be created for you.
    """

    key = "create"
    aliases = []
    locks = "cmd:all()"
    arg_regex = r"\s.*?|$"

    def func(self):
        self.caller.msg(
            "\n|yThe 'create' command has been retired.|n"
            "\nJust type |wconnect|n to sign in with your wallet."
            "\nIf you don't have an account yet, one will be created for you."
        )
