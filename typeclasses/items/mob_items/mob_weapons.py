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

from typeclasses.items.weapons.axe_nft_item import AxeMixin
from typeclasses.items.weapons.battleaxe_nft_item import BattleaxeMixin
from typeclasses.items.weapons.blowgun_nft_item import BlowgunMixin
from typeclasses.items.weapons.bola_nft_item import BolaMixin
from typeclasses.items.weapons.bow_nft_item import BowMixin
from typeclasses.items.weapons.club_nft_item import ClubMixin
from typeclasses.items.weapons.crossbow_nft_item import CrossbowMixin
from typeclasses.items.weapons.dagger_nft_item import DaggerMixin
from typeclasses.items.weapons.greatclub_nft_item import GreatclubMixin
from typeclasses.items.weapons.greatsword_nft_item import GreatswordMixin
from typeclasses.items.weapons.hammer_nft_item import HammerMixin
from typeclasses.items.weapons.lance_nft_item import LanceMixin
from typeclasses.items.weapons.longsword_nft_item import LongswordMixin
from typeclasses.items.weapons.mace_nft_item import MaceMixin
from typeclasses.items.weapons.ninjato_nft_item import NinjatoMixin
from typeclasses.items.weapons.nunchaku_nft_item import NunchakuMixin
from typeclasses.items.weapons.rapier_nft_item import RapierMixin
from typeclasses.items.weapons.sai_nft_item import SaiMixin
from typeclasses.items.weapons.shortsword_nft_item import ShortswordMixin
from typeclasses.items.weapons.shuriken_nft_item import ShurikenMixin
from typeclasses.items.weapons.sling_nft_item import SlingMixin
from typeclasses.items.weapons.spear_nft_item import SpearMixin
from typeclasses.items.weapons.staff_nft_item import StaffMixin


class MobAxe(AxeMixin, MobWeapon):
    """Mob handaxe — identical combat mechanics to AxeNFTItem."""
    pass


class MobBattleaxe(BattleaxeMixin, MobWeapon):
    """Mob battleaxe — identical combat mechanics to BattleaxeNFTItem."""
    pass


class MobBlowgun(BlowgunMixin, MobWeapon):
    """Mob blowgun — identical combat mechanics to BlowgunNFTItem."""
    pass


class MobBola(BolaMixin, MobWeapon):
    """Mob bola — identical combat mechanics to BolaNFTItem."""
    pass


class MobBow(BowMixin, MobWeapon):
    """Mob bow — identical combat mechanics to BowNFTItem."""
    pass


class MobClub(ClubMixin, MobWeapon):
    """Mob club — identical combat mechanics to ClubNFTItem."""
    pass


class MobCrossbow(CrossbowMixin, MobWeapon):
    """Mob crossbow — identical combat mechanics to CrossbowNFTItem."""
    pass


class MobDagger(DaggerMixin, MobWeapon):
    """Mob dagger — identical combat mechanics to DaggerNFTItem."""
    pass


class MobGreatclub(GreatclubMixin, MobWeapon):
    """Mob greatclub — identical combat mechanics to GreatclubNFTItem."""
    pass


class MobGreatsword(GreatswordMixin, MobWeapon):
    """Mob greatsword — identical combat mechanics to GreatswordNFTItem."""
    pass


class MobHammer(HammerMixin, MobWeapon):
    """Mob hammer — identical combat mechanics to HammerNFTItem."""
    pass


class MobLance(LanceMixin, MobWeapon):
    """Mob lance — identical combat mechanics to LanceNFTItem."""
    pass


class MobLongsword(LongswordMixin, MobWeapon):
    """Mob longsword — identical combat mechanics to LongswordNFTItem."""
    pass


class MobMace(MaceMixin, MobWeapon):
    """Mob mace — identical combat mechanics to MaceNFTItem."""
    pass


class MobNinjato(NinjatoMixin, MobWeapon):
    """Mob ninjato — identical combat mechanics to NinjatoNFTItem."""
    pass


class MobNunchaku(NunchakuMixin, MobWeapon):
    """Mob nunchaku — identical combat mechanics to NunchakuNFTItem."""
    pass


class MobRapier(RapierMixin, MobWeapon):
    """Mob rapier — identical combat mechanics to RapierNFTItem."""
    pass


class MobSai(SaiMixin, MobWeapon):
    """Mob sai — identical combat mechanics to SaiNFTItem."""
    pass


class MobShortsword(ShortswordMixin, MobWeapon):
    """Mob shortsword — identical combat mechanics to ShortswordNFTItem."""
    pass


class MobShuriken(ShurikenMixin, MobWeapon):
    """Mob shuriken — identical combat mechanics to ShurikenNFTItem.

    Note: consumable mechanics (move on throw, auto-equip next) are
    NFT-specific and stay on ShurikenNFTItem. Mob shurikens do not
    consume on throw.
    """
    pass


class MobSling(SlingMixin, MobWeapon):
    """Mob sling — identical combat mechanics to SlingNFTItem."""
    pass


class MobSpear(SpearMixin, MobWeapon):
    """Mob spear — identical combat mechanics to SpearNFTItem."""
    pass


class MobStaff(StaffMixin, MobWeapon):
    """Mob staff — identical combat mechanics to StaffNFTItem."""
    pass
