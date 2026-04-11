"""
Add pgvector support for NPC memory embeddings.

On PostgreSQL (Railway staging/production):
  - Enables the ``vector`` extension.
  - Adds ``embedding_vector`` column (vector(1536)).
  - Creates an HNSW index for fast cosine similarity search.
  - Populates ``embedding_vector`` from existing binary ``embedding`` data.

On SQLite (local dev):
  - The column is created as a text field (unused).
  - Extension / index / data migration steps are safely skipped.
"""

import numpy as np
from django.db import migrations

from pgvector.django import VectorField


# ── Conditional helpers (only act on PostgreSQL) ─────────────────────


def create_pgvector_extension(apps, schema_editor):
    """Enable the pgvector extension — PostgreSQL only."""
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS vector")


def add_hnsw_index(apps, schema_editor):
    """Create an HNSW index for cosine similarity — PostgreSQL only."""
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            "CREATE INDEX npcmemory_embedding_hnsw "
            "ON ai_memory_npcmemory USING hnsw (embedding_vector vector_cosine_ops) "
            "WITH (m = 16, ef_construction = 64)"
        )


def drop_hnsw_index(apps, schema_editor):
    """Drop the HNSW index — reverse of add_hnsw_index."""
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP INDEX IF EXISTS npcmemory_embedding_hnsw")


def populate_vectors(apps, schema_editor):
    """
    Back-fill ``embedding_vector`` from existing binary ``embedding`` blobs.

    Idempotent — safe to re-run. Skipped on SQLite.
    """
    if schema_editor.connection.vendor != "postgresql":
        return

    NpcMemory = apps.get_model("ai_memory", "NpcMemory")
    for mem in NpcMemory.objects.using("ai_memory").exclude(embedding=None):
        try:
            vec = np.frombuffer(bytes(mem.embedding), dtype=np.float32).tolist()
            mem.embedding_vector = vec
            mem.save(using="ai_memory", update_fields=["embedding_vector"])
        except Exception:
            # Skip malformed blobs silently — they'll just lack a vector.
            pass


class Migration(migrations.Migration):

    # HNSW index creation can block if run inside a transaction.
    atomic = False

    dependencies = [
        ("ai_memory", "0001_initial"),
    ]

    operations = [
        # 1. Enable pgvector extension (Postgres only, no-op on SQLite).
        migrations.RunPython(
            create_pgvector_extension,
            migrations.RunPython.noop,
        ),
        # 2. Add the vector column.
        migrations.AddField(
            model_name="npcmemory",
            name="embedding_vector",
            field=VectorField(dimensions=1536, null=True, blank=True),
        ),
        # 3. Create HNSW index for cosine search (Postgres only).
        migrations.RunPython(
            add_hnsw_index,
            drop_hnsw_index,
        ),
        # 4. Back-fill vector data from existing binary blobs (Postgres only).
        migrations.RunPython(
            populate_vectors,
            migrations.RunPython.noop,
        ),
    ]
