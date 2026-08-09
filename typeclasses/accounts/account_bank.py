from evennia.objects.objects import DefaultObject
from evennia.typeclasses.attributes import AttributeProperty
from typeclasses.mixins.fungible_inventory import FungibleInventoryMixin


class AccountBank(FungibleInventoryMixin, DefaultObject):
    """
    Account-level inventory container for NFTs and fungibles.

    One per account, created in Account.at_account_creation().
    Has no physical location in the game world. Items move between
    this and characters via bank/unbank (at a bank room in-game).
    """

    wallet_address = AttributeProperty(default=None)

    def at_object_creation(self):
        super().at_object_creation()
        self.at_fungible_init()
        self._stamp_global()

    def _stamp_global(self):
        """Mark this bank visible from every shard.

        A bank belongs to an account, not to a character, so an account's
        characters must reach it from whichever shard they are on. That
        is what the ``"*"`` sentinel is for: each shard's auto-filter is
        ``shard_id IN (<this shard>, "*")``.

        Banks are created on the router (chargen) or in monolith, and the
        router runs unscoped — so nothing auto-stamps and the row would
        otherwise land ``NULL``. ``NULL`` matches no shard's filter and
        raises nothing, leaving the bank invisible in-game with no error.
        Stamping here rather than at each call site means every creation
        path gets it, including ones not written yet.

        The write is a first stamp on a ``NULL`` column, not a mutation,
        so it does not trip the library's tenant-column immutability
        check. On a shard the auto-stamp would already have written that
        shard's id and this would raise — correctly, since a bank created
        on a shard is a bug (see ``ensure_bank``'s role guard).
        """
        from evennia_shards import ROLE_MONOLITH, get_role
        from evennia_shards.tenancy import GLOBAL_SHARD_ID

        if get_role() == ROLE_MONOLITH:
            # No shard_id column exists in monolith.
            return

        self.shard_id = GLOBAL_SHARD_ID
        self.save()
        self.flush_from_cache(force=True)
