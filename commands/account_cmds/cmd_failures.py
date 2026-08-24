"""
Superuser command to list operations that need manual reconciliation.

The happy path is recorded on the ledger and in the transfer and
transaction logs. This reads the exceptions list — the one place to ask
"has anything failed?" — and lets an operator mark a row done once they
have put it right.

Usage (OOC, superuser only):
    failures            — list unresolved failures
    failures all        — include ones already resolved
    failures <id>       — show one in full, error text included
    failures done <id> = <note>
                        — mark one resolved, with a note on what was done
"""

from evennia import Command


class CmdFailures(Command):
    """
    List operations that left on-chain and in-game state disagreeing.

    Each row is something no transaction could put right, because the
    ledger had already moved by the time the game-side write failed. They
    need a person, which is why they are collected rather than retried.

    Usage:
        failures
        failures all
        failures <id>
        failures done <id> = <note>

    Examples:
        failures
        failures 3
        failures done 3 = credited 20 gold by hand, tx confirmed on ledger
    """

    key = "failures"
    aliases = ["reconfailures"]
    locks = "cmd:id(1) and is_ooc()"
    help_category = "Blockchain"

    def func(self):
        from blockchain.xrpl.models import ReconciliationFailure

        args = self.args.strip()

        if args.startswith("done"):
            self._resolve(args[len("done"):].strip())
            return

        if args.isdigit():
            self._show(int(args))
            return

        show_all = args == "all"
        rows = ReconciliationFailure.objects.all()
        if not show_all:
            rows = rows.filter(resolved=False)

        if not rows:
            self.caller.msg(
                "|gNothing outstanding.|n" if not show_all
                else "|gNo failures recorded.|n"
            )
            return

        lines = [
            "|w%-5s %-26s %-14s %-10s %s|n"
            % ("ID", "Operation", "Character", "Amount", "When"),
        ]
        for row in rows:
            mark = "|g[done]|n " if row.resolved else ""
            lines.append(
                "%-5s %-26s %-14s %-10s %s%s" % (
                    row.id,
                    row.operation[:26],
                    (row.character_key or "-")[:14],
                    f"{row.amount or ''} {row.currency_code or ''}".strip()[:10],
                    row.created_at.strftime("%Y-%m-%d %H:%M"),
                    f"  {mark}" if mark else "",
                )
            )
        lines.append("")
        lines.append("|xfailures <id> for detail.|n")
        self.caller.msg("\n".join(lines))

    def _show(self, row_id):
        """Print one failure in full."""
        from blockchain.xrpl.models import ReconciliationFailure

        row = ReconciliationFailure.objects.filter(id=row_id).first()
        if not row:
            self.caller.msg(f"|rNo failure with id {row_id}.|n")
            return

        self.caller.msg(
            f"|wFailure #{row.id}|n\n"
            f"  Operation:  {row.operation}\n"
            f"  Wallet:     {row.wallet_address}\n"
            f"  Character:  {row.character_key or '-'}\n"
            f"  Amount:     {row.amount or '-'} {row.currency_code or ''}\n"
            f"  Tx hash:    {row.tx_hash or '-'}\n"
            f"  When:       {row.created_at}\n"
            f"  Resolved:   {'yes' if row.resolved else 'no'}\n"
            f"  Note:       {row.resolved_note or '-'}\n"
            f"  Error:      {row.error}"
        )

    def _resolve(self, args):
        """Mark a failure resolved: '<id> = <note>'."""
        from blockchain.xrpl.models import ReconciliationFailure

        if "=" not in args:
            self.caller.msg(
                "|rUsage: failures done <id> = <what you did>|n"
            )
            return

        raw_id, note = args.split("=", 1)
        raw_id, note = raw_id.strip(), note.strip()

        if not raw_id.isdigit():
            self.caller.msg(f"|r'{raw_id}' is not an id.|n")
            return
        if not note:
            self.caller.msg("|rSay what was done — the note is the point.|n")
            return

        row = ReconciliationFailure.objects.filter(id=int(raw_id)).first()
        if not row:
            self.caller.msg(f"|rNo failure with id {raw_id}.|n")
            return

        row.resolved = True
        row.resolved_note = note
        row.save(update_fields=["resolved", "resolved_note", "updated_at"])
        self.caller.msg(f"|gFailure #{row.id} marked resolved.|n")
