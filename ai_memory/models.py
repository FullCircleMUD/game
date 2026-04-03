"""
AI Memory models — three embedding-backed memory systems for NPC intelligence.

All models live in the ``ai_memory`` database (separate from Evennia's game DB)
so memories survive game DB wipes. Two embedding fields coexist on each model
for dual-backend support:

- ``embedding`` (BinaryField) — numpy binary blob, used on SQLite (local dev).
- ``embedding_vector`` (VectorField) — pgvector native column, used on
  PostgreSQL (Railway staging/production). Indexed via HNSW for
  sub-linear cosine similarity search.

See design docs:
- ``NpcMemory``: DATABASE.md § pgvector for AI Memory
- ``CombatMemory``: COMBAT_AI_MEMORY.md
- ``LoreMemory``: LORE_MEMORY.md
- Overview: NPC_MOB_ARCHITECTURE.md § Three Memory Systems
"""

from django.db import models

from pgvector.django import VectorField


class NpcMemory(models.Model):
    """
    A single conversation exchange between an NPC and a speaker.

    Stores both the raw text and an optional embedding vector for
    semantic search. The ``npc_name`` and ``speaker_name`` fields enable
    matching across game DB wipes where Evennia object IDs change —
    search falls back to name-based matching when ID-based returns
    nothing.
    """

    npc_id = models.IntegerField(db_index=True)
    speaker_id = models.IntegerField(db_index=True)
    speaker_name = models.CharField(max_length=80)
    npc_name = models.CharField(max_length=80)
    user_message = models.TextField()
    assistant_message = models.TextField()
    summary = models.TextField(blank=True, default="")
    embedding = models.BinaryField(null=True, blank=True)
    embedding_vector = VectorField(dimensions=1536, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    interaction_type = models.CharField(max_length=20, default="say")

    class Meta:
        app_label = "ai_memory"
        verbose_name = "NPC Memory"
        verbose_name_plural = "NPC Memories"
        indexes = [
            models.Index(fields=["npc_id", "created_at"]),
            models.Index(fields=["npc_id", "speaker_id"]),
            models.Index(fields=["npc_name", "created_at"]),
            models.Index(fields=["npc_name", "speaker_name"]),
        ]

    def __str__(self):
        return (
            f"{self.npc_name} ↔ {self.speaker_name} "
            f"({self.created_at:%Y-%m-%d %H:%M})"
        )


class CombatMemory(models.Model):
    """
    A single completed combat encounter, recorded for tactical learning.

    After every fight, the mob records a structured summary: party
    composition, tactics used by both sides, and outcome. Before a new
    fight, a strategy bot searches this table for similar encounters to
    synthesise a tactical plan.

    Memory scope is determined by query strategy, not schema:
    - **Per-type:** query by ``mob_type`` (all gnolls share learnings).
    - **Per-instance:** query by ``mob_name`` (a named boss remembers).
    - **Hybrid:** instance first, type fallback.

    See design/COMBAT_AI_MEMORY.md for the full architecture.
    """

    # ── Who fought ──
    mob_type = models.CharField(max_length=80, db_index=True)
    mob_level = models.IntegerField()
    mob_name = models.CharField(max_length=80, db_index=True)

    # ── Party composition (structured for filtering + future ML) ──
    party_composition = models.JSONField()
    # Example: [{"name": "Bob", "class": "warrior", "level": 10},
    #           {"name": "Alice", "class": "cleric", "level": 9}]
    party_size = models.IntegerField(db_index=True)

    # ── What happened ──
    mob_tactics = models.TextField()
    enemy_tactics = models.TextField()
    rounds_survived = models.IntegerField()

    # ── Outcome ──
    outcome = models.CharField(max_length=20, db_index=True)
    # "win", "loss", "fled", "draw"
    hp_remaining_pct = models.FloatField()
    # 0.0 = dead, 0.95 = easy win. Captures fight margin.

    # ── Embedding (dual-backend) ──
    summary = models.TextField()
    embedding = models.BinaryField(null=True, blank=True)
    embedding_vector = VectorField(dimensions=1536, null=True, blank=True)

    # ── Metadata ──
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "ai_memory"
        verbose_name = "Combat Memory"
        verbose_name_plural = "Combat Memories"
        indexes = [
            models.Index(fields=["mob_type", "created_at"]),
            models.Index(fields=["mob_type", "party_size"]),
            models.Index(fields=["mob_type", "outcome"]),
            models.Index(fields=["mob_name", "created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.mob_name} vs {self.party_size} players — "
            f"{self.outcome} ({self.created_at:%Y-%m-%d %H:%M})"
        )


class LoreMemory(models.Model):
    """
    A single piece of world knowledge, embedded for semantic retrieval.

    Lore is authored once, tagged with scope, and retrieved dynamically
    at prompt-build time based on what the player is asking about and
    which scopes the NPC has access to.

    Scope levels (broadest → narrowest):
    - **continental:** major history, geography — every NPC knows this.
    - **regional:** zone-level history — NPCs in that zone.
    - **local:** district-level knowledge — NPCs in that district.
    - **faction:** guild/faction secrets — NPCs with matching tags.

    See design/LORE_MEMORY.md for the full architecture.
    """

    # ── Identity ──
    title = models.CharField(max_length=200)
    content = models.TextField()

    # ── Scope ──
    scope_level = models.CharField(max_length=20, db_index=True)
    # "continental", "regional", "local", "faction"
    scope_tags = models.JSONField(default=list)
    # Examples:
    #   continental: []
    #   regional:    ["millholm"]
    #   local:       ["millholm_town"]
    #   faction:     ["mages_guild"]
    #   multi-tag:   ["millholm", "mages_guild"]

    # ── Embedding (dual-backend) ──
    embedding = models.BinaryField(null=True, blank=True)
    embedding_vector = VectorField(dimensions=1536, null=True, blank=True)

    # ── Metadata ──
    source = models.CharField(max_length=200, blank=True, default="")
    # Where this lore originated: "WORLD.md", "millholm/town.py", "manual", etc.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ai_memory"
        verbose_name = "Lore Memory"
        verbose_name_plural = "Lore Memories"
        indexes = [
            models.Index(fields=["scope_level"]),
            models.Index(fields=["scope_level", "created_at"]),
        ]

    def __str__(self):
        tags = ", ".join(self.scope_tags) if self.scope_tags else "global"
        return f"{self.title} ({self.scope_level}: {tags})"
