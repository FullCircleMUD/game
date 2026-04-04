"""
MobItem — base typeclass for all non-NFT mob equipment.

Mirrors BaseNFTItem in the NFT hierarchy but without blockchain
tracking, durability, height awareness, hidden/invisible mechanics,
or item restriction gates.

MobItem instances are deleted on mob death via class-based filtering
in CombatMob._create_corpse() — they never transfer to corpses or
enter the player economy.
"""

from evennia.objects.objects import DefaultObject
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.search import search_object


class MobItem(DefaultObject):
    """
    Base class for all mob-only items (weapons, armour, consumables).

    Stripped vs BaseNFTItem:
        - No HeightAwareMixin (mob's own height handles this)
        - No HiddenObjectMixin (mob hides, gear goes with it)
        - No ItemRestrictionMixin (builders enforce at build time)
        - No DurabilityMixin (mob items are ephemeral)
        - No NFT tracking (no token_id, no NFTService calls)
    """

    weight = AttributeProperty(0.0)

    def reduce_durability(self, amount):
        """No-op — mob items have no durability. Stubbed because
        execute_attack() calls this on every hit and parry."""
        pass

    @staticmethod
    def spawn_mob_item(prototype_key, location=None):
        """
        Create a mob item from a prototype dict.

        Reads the raw prototype dict (not Evennia's normalised version)
        to access the ``mob_typeclass`` field, then uses Evennia's
        spawn() with the mob typeclass and all stat fields applied.
        No token_id, no NFTService, no blockchain tracking.

        Args:
            prototype_key: str — prototype_key to look up (e.g. "iron_dagger")
            location: Evennia object to place the item (mob, room, etc.)

        Returns:
            The created mob item object, or None if prototype not found
            or has no mob_typeclass defined.
        """
        from evennia.prototypes.spawner import spawn as evennia_spawn

        # Load the raw prototype dict from the module — Evennia's
        # search_prototype() normalises away custom fields like
        # mob_typeclass into attrs, so we access the source directly.
        proto = _get_raw_prototype(prototype_key)
        if not proto:
            return None

        mob_tc = proto.get("mob_typeclass")
        if not mob_tc:
            return None

        # Recycle bin as home — orphaned items get cleaned up
        recycle_results = search_object("nft_recycle_bin", exact=True)
        recycle_bin = recycle_results[0] if recycle_results else None

        # Build spawn dict — use mob typeclass instead of NFT typeclass
        spawn_dict = dict(proto)
        spawn_dict["typeclass"] = mob_tc
        spawn_dict["location"] = location
        if recycle_bin:
            spawn_dict["home"] = recycle_bin
        # Remove fields that are NFT-only or cause Evennia conflicts
        spawn_dict.pop("mob_typeclass", None)
        spawn_dict.pop("max_durability", None)
        spawn_dict.pop("prototype_key", None)
        spawn_dict.pop("prototype_parent", None)
        spawn_dict.pop("excluded_classes", None)
        spawn_dict.pop("required_classes", None)

        obj = evennia_spawn(spawn_dict)[0]
        return obj


def _get_raw_prototype(prototype_key):
    """
    Look up a raw prototype dict by key from the prototype modules.

    Evennia's search_prototype() normalises custom fields into an attrs
    list, losing top-level access. This function scans the registered
    prototype modules for the original dict with matching prototype_key.
    """
    from django.conf import settings
    from importlib import import_module
    import inspect

    for module_path in getattr(settings, "PROTOTYPE_MODULES", []):
        try:
            module = import_module(module_path)
        except ImportError:
            continue
        for _name, obj in inspect.getmembers(module):
            if isinstance(obj, dict) and obj.get("prototype_key") == prototype_key:
                return obj
    return None
