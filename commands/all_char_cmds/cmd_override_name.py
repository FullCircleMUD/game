"""
@name, refusing to rename characters and accounts.

The XRPL mirror records ownership against the character's *name*:
``FungibleGameState.character_key`` and ``NFTGameState.character_key`` are
CharFields holding the key, not a foreign key or a UUID. Renaming a
character therefore silently orphans every gold, resource and NFT row it
owns — the rows keep the old name, the character answers to the new one,
and nothing raises. The player simply stops owning their possessions.

Accounts are refused for the same reason applied earlier: the mirror keys
on wallet address rather than account name today, so a rename is
currently harmless there — but the account name is the login identity, and
allowing one rename to be safe while the other is not invites the wrong
lesson. Both are refused; the wallet is the identity for both.

This closes the accidental door, not the deliberate one. A superuser can
still assign ``char.key`` through ``py``, and no command override can
prevent that. It is meant to stop a builder renaming a character in the
ordinary course of building, which is a plausible mistake with expensive
and invisible consequences.

The proper fix is to key the mirror on something immutable. That is a
230-call-site refactor across the layer that must never be wrong, so it
waits for a reason better than a door nobody has walked through.
"""

from evennia.commands.default.building import CmdName as DefaultCmdName


class CmdName(DefaultCmdName):
    """
    change the name and/or aliases of an object

    Usage:
      name <obj> = <newname>;alias1;alias2

    Rename an object to something new.

    Characters and accounts cannot be renamed — the blockchain ownership
    records are keyed on the character's name, so renaming one would
    detach it from its gold, resources and items.
    """

    def func(self):
        caller = self.caller

        if not self.args or not self.lhs_objs:
            return super().func()

        objname = self.lhs_objs[0]["name"]

        # Account mode — `name *someone = newname`. Refused before the
        # search, so the answer does not depend on whether the account
        # was found.
        if objname.startswith("*"):
            caller.msg(
                "|rAccounts cannot be renamed.|n\n"
                "An account is identified by its wallet address; the name "
                "is how the player signs in and appears in the payment log."
            )
            return

        obj = caller.search(objname)
        if not obj:
            return

        if self._is_actor(obj):
            caller.msg(
                f"|r{obj.key} cannot be renamed.|n\n"
                "Blockchain ownership is recorded against a character's "
                "name, so renaming would detach them from their gold, "
                "resources and items with no error and no way back."
            )
            return

        return super().func()

    @staticmethod
    def _is_actor(obj):
        """Whether this object is a character rather than a thing.

        Tested by typeclass rather than by looking for an account on it:
        a character sitting offline has no account attached, and that is
        exactly when a builder is most likely to be renaming one.
        """
        from evennia.objects.objects import DefaultCharacter

        return isinstance(obj, DefaultCharacter)
