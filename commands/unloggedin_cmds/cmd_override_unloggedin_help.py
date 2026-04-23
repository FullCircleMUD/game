"""
Override of Evennia's default unlogged-in help command.

Reflects the FCM login flow (wallet-based via Xaman) rather than the
stock username/password create + connect flow.
"""

from django.conf import settings
from evennia.utils import utils

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)


class CmdUnconnectedHelp(COMMAND_DEFAULT_CLASS):
    """
    get help when in unconnected state

    Usage:
      help

    Shows the commands available before login and explains how to
    create or connect an account via Xaman wallet sign-in.
    """

    key = "help"
    aliases = ["h", "?"]
    locks = "cmd:all()"

    def func(self):
        string = """
You are not yet logged into the game. Commands available at this point:

  |wconnect|n - create a new OR connect with an existing account
  |wlook|n - re-show the connection screen
  |whelp|n - show this help
  |wencoding|n - change the text encoding to match your client
  |wscreenreader|n - make the server more suitable for use with screen readers
  |wquit|n - abort the connection

Create an account by entering |wconnect|n, confirming with a Y,
opening the Xaman link in a new tab & signing to verify your xrpl address.

You can use the |wlook|n command if you want to see the connect screen again.

"""

        if settings.STAFF_CONTACT_EMAIL:
            string += "For support, please contact: %s" % settings.STAFF_CONTACT_EMAIL
        self.msg(string)
