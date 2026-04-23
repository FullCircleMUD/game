"""Seed NFTItemType rows for 5 BASIC-tier scrolls missed in 0001_initial.

ScrollDistributor was emitting hourly "no NFTItemType for scroll_<key>" warnings
for feather_fall, fear, raise_skeleton, light_spell, and create_water because
populate_knowledge_config auto-enrolls every spell with a min_mastery value but
0001_initial's seed list omitted these five. This migration inserts the missing
rows using the same shape as the existing scroll entries.
"""

from django.db import migrations


_SPELL_SCROLL_TC = "typeclasses.items.consumables.spell_scroll_nft_item.SpellScrollNFTItem"

NEW_SPELL_SCROLLS = [
    {
        "name": "Scroll of Feather Fall",
        "typeclass": _SPELL_SCROLL_TC,
        "prototype_key": "feather_fall_scroll",
        "description": "A weightless scroll that drifts slowly to the ground when dropped. The parchment is pale and thin, dotted with a few stray downy feathers pressed into the fibres.",
    },
    {
        "name": "Scroll of Fear",
        "typeclass": _SPELL_SCROLL_TC,
        "prototype_key": "fear_scroll",
        "description": "A blackened scroll bound with a twist of something that looks uncomfortably like hair. Holding it long makes the back of your neck prickle.",
    },
    {
        "name": "Scroll of Raise Skeleton",
        "typeclass": _SPELL_SCROLL_TC,
        "prototype_key": "raise_skeleton_scroll",
        "description": "A yellowed scroll drawn on parchment so dry it seems ready to crumble. Tiny sketches of jointed bones run along the margin, as if waiting to be called up.",
    },
    {
        "name": "Scroll of Light",
        "typeclass": _SPELL_SCROLL_TC,
        "prototype_key": "light_spell_scroll",
        "description": "A crisp scroll whose inked runes glow with a steady, soft radiance. Shadows ease back wherever you carry it.",
    },
    {
        "name": "Scroll of Create Water",
        "typeclass": _SPELL_SCROLL_TC,
        "prototype_key": "create_water_scroll",
        "description": "A cool, slightly damp scroll that beads with condensation in the palm. The ink is the deep blue of still water at dusk.",
    },
]


def seed_missing_scrolls(apps, schema_editor):
    NFTItemType = apps.get_model("xrpl", "NFTItemType")
    for item in NEW_SPELL_SCROLLS:
        NFTItemType.objects.update_or_create(
            name=item["name"],
            defaults=item,
        )


def remove_missing_scrolls(apps, schema_editor):
    NFTItemType = apps.get_model("xrpl", "NFTItemType")
    NFTItemType.objects.filter(
        name__in=[item["name"] for item in NEW_SPELL_SCROLLS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("xrpl", "0002_rename_xrpl_bulletinli_expires_idx_xrpl_bullet_expires_71139f_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_missing_scrolls, remove_missing_scrolls),
    ]
