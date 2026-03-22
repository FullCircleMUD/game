"""
AI Memory app — initial migration.

Creates the NpcMemory table for persistent NPC conversation memory
with optional embedding vectors.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="NpcMemory",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("npc_id", models.IntegerField(db_index=True)),
                ("speaker_id", models.IntegerField(db_index=True)),
                ("speaker_name", models.CharField(max_length=80)),
                ("npc_name", models.CharField(max_length=80)),
                ("user_message", models.TextField()),
                ("assistant_message", models.TextField()),
                ("summary", models.TextField(blank=True, default="")),
                ("embedding", models.BinaryField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "interaction_type",
                    models.CharField(default="say", max_length=20),
                ),
            ],
            options={
                "verbose_name": "NPC Memory",
                "verbose_name_plural": "NPC Memories",
            },
        ),
        migrations.AddIndex(
            model_name="npcmemory",
            index=models.Index(
                fields=["npc_id", "created_at"],
                name="ai_memory_n_npc_id_a1b2c3_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="npcmemory",
            index=models.Index(
                fields=["npc_id", "speaker_id"],
                name="ai_memory_n_npc_id_d4e5f6_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="npcmemory",
            index=models.Index(
                fields=["npc_name", "created_at"],
                name="ai_memory_n_npc_na_g7h8i9_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="npcmemory",
            index=models.Index(
                fields=["npc_name", "speaker_name"],
                name="ai_memory_n_npc_na_j0k1l2_idx",
            ),
        ),
    ]
