"""
LootMobMixin — declares the spawn-loot capacity slots a mob can carry.

evennia_mob_spawner applies a rule's YAML-declared attrs: via bare
setattr(mob, attr_name, attr_val) at spawn time. That only persists if
attr_name is a declared AttributeProperty descriptor somewhere in the
typeclass's MRO — without one, setattr() silently sets a plain,
non-persisted Python attribute that vanishes with the object (the
library now logs a WARN when this happens; see _persists_as_attribute
in evennia_mob_spawner.script).

This mixin supplies those descriptors so the router's spawn system
(blockchain.xrpl.services.spawn) can read real, persisted capacity off
any mob. Every field defaults to "no loot" — the actual numbers stay
entirely YAML-driven per mob-spawner rule; this mixin never sets a
real value itself.

Field names match blockchain.xrpl.services.spawn.reader.CATEGORY_MAX_ATTR
— one slot per spawn category the router understands.
"""

from evennia.typeclasses.attributes import AttributeProperty


class LootMobMixin:
    """Mixin declaring the loot-capacity attributes a mob can carry.

    Include in any mob typeclass that should be eligible to carry
    router-placed loot. All defaults are "no loot" (0 / empty dict);
    a mob-spawner rule's attrs: block overrides these per-rule.
    """

    spawn_gold_max = AttributeProperty(0)
    spawn_resources_max = AttributeProperty({})
    spawn_scrolls_max = AttributeProperty({})
    spawn_recipes_max = AttributeProperty({})
    spawn_nfts_max = AttributeProperty({})
