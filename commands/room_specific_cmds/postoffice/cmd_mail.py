"""
Mail command — character-to-character asynchronous messaging.

Available at Post Office rooms. Uses Evennia's Msg class for storage
with category="mail" tags for filtering.

Usage:
    mail                             — list inbox
    mail <#>                         — read a specific message
    mail <character>=<subject>/<body> — send mail
    mail reply <#>=<message>         — reply to a message
    mail delete <#>                  — delete a message
"""

from evennia.commands.command import Command
from evennia.comms.models import Msg

from commands.command import FCMCommandMixin
from evennia.utils import create, evtable
from evennia.objects.models import ObjectDB

_WIDTH = 78


class CmdMail(FCMCommandMixin, Command):
    """
    Send and receive mail at the Post Office.

    Usage:
        mail                              — view your inbox
        mail <#>                          — read message number #
        mail <character>=<subject>/<body>  — send a message
        mail reply <#>=<message>          — reply to message #
        mail delete <#>                   — delete message #
    """

    key = "mail"
    aliases = ["@mail"]
    locks = "cmd:all()"
    help_category = "Communication"
    # Use = as separator for send/reply syntax
    rhs_split = ("=",)

    def parse(self):
        super().parse()
        self.args = self.args.strip() if self.args else ""

        # Detect subcommands: "mail reply ..." or "mail delete ..."
        self.subcmd = None
        lower = self.args.lower()
        if lower.startswith("reply "):
            self.subcmd = "reply"
            self.args = self.args[6:].strip()
        elif lower.startswith("delete "):
            self.subcmd = "delete"
            self.args = self.args[7:].strip()

        # Re-split lhs/rhs after subcommand extraction
        if "=" in self.args:
            parts = self.args.split("=", 1)
            self.lhs = parts[0].strip()
            self.rhs = parts[1].strip()
        else:
            self.lhs = self.args
            self.rhs = None

    def func(self):
        caller = self.caller

        if self.subcmd == "delete":
            self._delete()
            return
        if self.subcmd == "reply":
            self._reply()
            return

        if not self.args:
            self._list_inbox()
            return

        # mail <#> — read a message
        if self.args.isdigit():
            self._read(int(self.args))
            return

        # mail <target>=<subject>/<body>
        if self.rhs:
            self._send()
            return

        caller.msg("Usage: mail <character>=<subject>/<message>")

    # ================================================================== #
    #  Inbox listing
    # ================================================================== #

    def _list_inbox(self):
        caller = self.caller
        mail = self._get_all_mail()

        if not mail:
            caller.msg("Your mailbox is empty.")
            return

        table = evtable.EvTable(
            "|wID|n", "|wFrom|n", "|wSubject|n", "|wDate|n", "|wStatus|n",
            border="none",
            align="l",
        )
        table.reformat_column(0, width=5)
        table.reformat_column(1, width=16)
        table.reformat_column(2, width=30)
        table.reformat_column(3, width=14)
        table.reformat_column(4, width=8)

        for i, msg in enumerate(mail, 1):
            sender = self._get_sender_name(msg)
            subject = msg.header or "(no subject)"
            date = msg.db_date_created.strftime("%b %d %H:%M")
            tags = msg.tags.get(category="mail", return_list=True)
            if "new" in tags:
                status = "|gNEW|n"
            else:
                status = "-"
            table.add_row(str(i), sender, subject[:28], date, status)

        caller.msg(f"|w--- Mailbox ({len(mail)} messages) ---|n\n{table}")

    # ================================================================== #
    #  Read a message
    # ================================================================== #

    def _read(self, num):
        caller = self.caller
        mail = self._get_all_mail()

        if num < 1 or num > len(mail):
            caller.msg(f"Invalid message number. You have {len(mail)} messages.")
            return

        msg = mail[num - 1]
        sender = self._get_sender_name(msg)
        date = msg.db_date_created.strftime("%Y-%m-%d %H:%M")
        subject = msg.header or "(no subject)"

        # Mark as read
        if "new" in msg.tags.get(category="mail", return_list=True):
            msg.tags.remove("new", category="mail")
            msg.tags.add("-", category="mail")

        caller.msg(
            f"\n{'-' * _WIDTH}\n"
            f"|wFrom:|n {sender}\n"
            f"|wDate:|n {date}\n"
            f"|wSubject:|n {subject}\n"
            f"{'-' * _WIDTH}\n"
            f"{msg.message}\n"
            f"{'-' * _WIDTH}"
        )

    # ================================================================== #
    #  Send a message
    # ================================================================== #

    def _send(self):
        caller = self.caller

        if not self.lhs or not self.rhs:
            caller.msg("Usage: mail <character>=<subject>/<message>")
            return

        target_name = self.lhs.strip()
        target = self._find_character(target_name)
        if not target:
            caller.msg(f"No character named '{target_name}' found.")
            return

        # Split subject/body
        if "/" in self.rhs:
            subject, body = self.rhs.split("/", 1)
            subject = subject.strip()
            body = body.strip()
        else:
            subject = self.rhs.strip()
            body = ""

        if not subject:
            caller.msg("You must provide a subject.")
            return

        if not body:
            caller.msg("You must provide a message body. Usage: mail <char>=<subject>/<body>")
            return

        # Create message
        new_msg = create.create_message(
            caller, body, receivers=target, header=subject,
        )
        new_msg.tags.add("new", category="mail")

        caller.msg(f"Mail sent to {target.key}: {subject}")

        # Notify recipient if online
        if target.has_account and target.sessions.count() > 0:
            target.msg(f"|yYou have received new mail from {caller.key}.|n")

    # ================================================================== #
    #  Reply
    # ================================================================== #

    def _reply(self):
        caller = self.caller

        if not self.lhs or not self.rhs:
            caller.msg("Usage: mail reply <#>=<message>")
            return

        if not self.lhs.isdigit():
            caller.msg("Usage: mail reply <#>=<message>")
            return

        num = int(self.lhs)
        mail = self._get_all_mail()

        if num < 1 or num > len(mail):
            caller.msg(f"Invalid message number. You have {len(mail)} messages.")
            return

        original = mail[num - 1]
        sender_name = self._get_sender_name(original)
        target = self._find_character(sender_name)
        if not target:
            caller.msg(f"Could not find character '{sender_name}' to reply to.")
            return

        subject = f"RE: {original.header or '(no subject)'}"
        body = self.rhs.strip()

        if not body:
            caller.msg("You must provide a reply message.")
            return

        new_msg = create.create_message(
            caller, body, receivers=target, header=subject,
        )
        new_msg.tags.add("new", category="mail")

        caller.msg(f"Reply sent to {target.key}: {subject}")

        if target.has_account and target.sessions.count() > 0:
            target.msg(f"|yYou have received new mail from {caller.key}.|n")

    # ================================================================== #
    #  Delete
    # ================================================================== #

    def _delete(self):
        caller = self.caller

        if not self.args or not self.args.isdigit():
            caller.msg("Usage: mail delete <#>")
            return

        num = int(self.args)
        mail = self._get_all_mail()

        if num < 1 or num > len(mail):
            caller.msg(f"Invalid message number. You have {len(mail)} messages.")
            return

        msg = mail[num - 1]
        subject = msg.header or "(no subject)"
        msg.delete()
        caller.msg(f"Deleted message #{num}: {subject}")

    # ================================================================== #
    #  Helpers
    # ================================================================== #

    def _get_all_mail(self):
        """Get all mail for this character, ordered by date."""
        return list(
            Msg.objects.get_by_tag(category="mail")
            .filter(db_receivers_objects=self.caller)
            .order_by("db_date_created")
        )

    def _get_sender_name(self, msg):
        """Get the sender's display name from a Msg object."""
        senders = msg.senders
        if senders:
            return senders[0].key
        return "Unknown"

    def _find_character(self, name):
        """Find a character by exact name (case-insensitive)."""
        matches = ObjectDB.objects.filter(
            db_key__iexact=name,
            db_typeclass_path__contains="character",
        )
        if matches.exists():
            return matches.first()
        return None

    @staticmethod
    def get_unread_count(character):
        """Return count of unread mail for a character. Used by login hook."""
        return (
            Msg.objects.get_by_tag("new", category="mail")
            .filter(db_receivers_objects=character)
            .count()
        )
