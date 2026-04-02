"""
Concrete mob weapon classes — one per weapon type.

Each class composes a weapon identity mixin (e.g. DaggerMixin) with
MobWeapon. All combat mechanics come from the shared mixin — these
are one-liners that exist solely so the spawn system can instantiate
the correct weapon type.

Weapon identity mixins live in the same file as their NFT counterpart
(e.g. DaggerMixin in dagger_nft_item.py) — single source of truth.
"""

from typeclasses.items.mob_items.mob_weapon import MobWeapon
from typeclasses.items.weapons.dagger_nft_item import DaggerMixin


class MobDagger(DaggerMixin, MobWeapon):
    """Mob dagger — identical combat mechanics to DaggerNFTItem."""
    pass
