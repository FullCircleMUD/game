"""Add UniqueConstraint(source, title) to LoreMemory.

Required for the standalone lore-import tool (in the FCM/lore repo)
to use INSERT ... ON CONFLICT (source, title) atomically. Also closes
a latent race in store_lore()'s get-then-create code path.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_memory", "0004_rename_ai_memory_c_mob_typ_a1b2c3_idx_ai_memory_c_mob_typ_2d74b3_idx_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="lorememory",
            constraint=models.UniqueConstraint(
                fields=("source", "title"),
                name="uniq_lorememory_source_title",
            ),
        ),
    ]
