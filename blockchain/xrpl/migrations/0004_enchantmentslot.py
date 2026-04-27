"""Schema for EnchantmentSlot (compliance-driven pre-disclosure of gem outcomes).

No seed data — slots are lazily created by EnchantmentService.preview_slot()
on first query for a given (output_table, mastery_level) pair. This avoids
loading typeclass code (races/classes used by roll_gem_enchantment) inside
the migration context, and means new entries in gem_tables.py auto-seed
without requiring a data migration.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("xrpl", "0003_seed_missing_scroll_nft_item_types"),
    ]

    operations = [
        migrations.CreateModel(
            name="EnchantmentSlot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("output_table", models.CharField(max_length=64)),
                ("mastery_level", models.PositiveSmallIntegerField()),
                ("slot_number", models.PositiveIntegerField(default=1)),
                ("current_outcome", models.JSONField()),
                ("rolled_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("output_table", "mastery_level"),
                        name="xrpl_enchant_slot_unique_table_mastery",
                    ),
                ],
            },
        ),
    ]
