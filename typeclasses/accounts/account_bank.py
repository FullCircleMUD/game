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
