"""
Add CombatMemory and LoreMemory tables.

CombatMemory: structured combat encounter records with embeddings for
the strategy bot system (see design/COMBAT_AI_MEMORY.md).

LoreMemory: scoped world knowledge with embeddings for dynamic NPC
knowledge retrieval (see design/LORE_MEMORY.md).

Both tables use the same dual-backend embedding pattern as NpcMemory:
VectorField on PostgreSQL (with HNSW index), BinaryField on SQLite.
"""

from django.db import migrations, models

from pgvector.django import VectorField


def create_hnsw_indexes(apps, schema_editor):
    """Create HNSW indexes for cosine similarity — PostgreSQL only."""
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "CREATE INDEX combatmemory_embedding_hnsw "
        "ON ai_memory_combatmemory USING hnsw (embedding_vector vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )
    schema_editor.execute(
        "CREATE INDEX lorememory_embedding_hnsw "
        "ON ai_memory_lorememory USING hnsw (embedding_vector vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def drop_hnsw_indexes(apps, schema_editor):
    """Drop the HNSW indexes — reverse of create_hnsw_indexes."""
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP INDEX IF EXISTS combatmemory_embedding_hnsw")
    schema_editor.execute("DROP INDEX IF EXISTS lorememory_embedding_hnsw")


class Migration(migrations.Migration):

    dependencies = [
        ("ai_memory", "0002_pgvector"),
    ]

    operations = [
        # ── CombatMemory ─────────────────────────────────────────────
        migrations.CreateModel(
            name="CombatMemory",
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
                ("mob_type", models.CharField(db_index=True, max_length=80)),
                ("mob_level", models.IntegerField()),
                ("mob_name", models.CharField(db_index=True, max_length=80)),
                ("party_composition", models.JSONField()),
                ("party_size", models.IntegerField(db_index=True)),
                ("mob_tactics", models.TextField()),
                ("enemy_tactics", models.TextField()),
                ("rounds_survived", models.IntegerField()),
                ("outcome", models.CharField(db_index=True, max_length=20)),
                ("hp_remaining_pct", models.FloatField()),
                ("summary", models.TextField()),
                ("embedding", models.BinaryField(blank=True, null=True)),
                (
                    "embedding_vector",
                    VectorField(blank=True, dimensions=1536, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Combat Memory",
                "verbose_name_plural": "Combat Memories",
            },
        ),
        migrations.AddIndex(
            model_name="combatmemory",
            index=models.Index(
                fields=["mob_type", "created_at"],
                name="ai_memory_c_mob_typ_a1b2c3_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="combatmemory",
            index=models.Index(
                fields=["mob_type", "party_size"],
                name="ai_memory_c_mob_typ_d4e5f6_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="combatmemory",
            index=models.Index(
                fields=["mob_type", "outcome"],
                name="ai_memory_c_mob_typ_g7h8i9_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="combatmemory",
            index=models.Index(
                fields=["mob_name", "created_at"],
                name="ai_memory_c_mob_nam_j0k1l2_idx",
            ),
        ),
        # ── LoreMemory ──────────────────────────────────────────────
        migrations.CreateModel(
            name="LoreMemory",
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
                ("title", models.CharField(max_length=200)),
                ("content", models.TextField()),
                ("scope_level", models.CharField(db_index=True, max_length=20)),
                ("scope_tags", models.JSONField(default=list)),
                ("embedding", models.BinaryField(blank=True, null=True)),
                (
                    "embedding_vector",
                    VectorField(blank=True, dimensions=1536, null=True),
                ),
                ("source", models.CharField(blank=True, default="", max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Lore Memory",
                "verbose_name_plural": "Lore Memories",
            },
        ),
        migrations.AddIndex(
            model_name="lorememory",
            index=models.Index(
                fields=["scope_level"],
                name="ai_memory_l_scope_l_m3n4o5_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="lorememory",
            index=models.Index(
                fields=["scope_level", "created_at"],
                name="ai_memory_l_scope_l_p6q7r8_idx",
            ),
        ),
        # ── HNSW indexes (PostgreSQL only) ───────────────────────────
        migrations.RunPython(
            create_hnsw_indexes,
            drop_hnsw_indexes,
        ),
    ]
