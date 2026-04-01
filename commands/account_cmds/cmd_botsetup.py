"""
Superuser command: create bot accounts from settings.

Reads BOT_ACCOUNT_USERNAMES, BOT_WALLET_ADDRESSES, and
BOT_PASSWORDS / BOT_DEFAULT_PASSWORD to create accounts
with wallet addresses pre-assigned. Idempotent — skips
accounts that already exist.
"""

from django.conf import settings
from evennia import Command


class CmdBotSetup(Command):
    """
    Create bot accounts from settings configuration.

    Usage:
        botsetup

    Creates all accounts listed in BOT_ACCOUNT_USERNAMES with their
    wallet addresses from BOT_WALLET_ADDRESSES. Passwords come from
    BOT_PASSWORDS (secret_settings.py) falling back to BOT_DEFAULT_PASSWORD.
    Idempotent — existing accounts are skipped.
    """

    key = "botsetup"
    locks = "cmd:id(1)"
    help_category = "Bots"

    def func(self):
        from evennia.accounts.models import AccountDB
        from evennia.utils.create import create_account

        usernames = getattr(settings, "BOT_ACCOUNT_USERNAMES", [])
        wallets = getattr(settings, "BOT_WALLET_ADDRESSES", {})
        passwords = getattr(settings, "BOT_PASSWORDS", {})
        default_pw = getattr(settings, "BOT_DEFAULT_PASSWORD", "changeme")

        if not usernames:
            self.msg("No bot accounts configured in BOT_ACCOUNT_USERNAMES.")
            return

        for name in usernames:
            existing = AccountDB.objects.filter(username=name).first()
            if existing:
                # Ensure wallet is set even on existing accounts
                wallet = wallets.get(name)
                if wallet:
                    current = existing.attributes.get("wallet_address")
                    if current != wallet:
                        existing.attributes.add("wallet_address", wallet)
                        self.msg(f"  |y{name}|n: already exists (#{existing.id}), updated wallet.")
                    else:
                        self.msg(f"  |y{name}|n: already exists (#{existing.id}), wallet OK.")
                else:
                    self.msg(f"  |y{name}|n: already exists (#{existing.id}), no wallet configured.")
                continue

            pw = passwords.get(name, default_pw)
            account = create_account(name, email=None, password=pw)
            self.msg(f"  |g{name}|n: created (#{account.id})")

            wallet = wallets.get(name)
            if wallet:
                account.attributes.add("wallet_address", wallet)
                self.msg(f"    wallet: {wallet}")

        self.msg(f"\n|gBot setup complete.|n {len(usernames)} account(s) processed.")
