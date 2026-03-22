"""
AI Memory models — persistent NPC memory with vector embeddings.

Stores conversation exchanges between NPCs and players, with optional
embedding vectors for semantic similarity search. Lives in a separate
``ai_memory`` SQLite database so memories survive game DB wipes.
"""

from django.db import models


class NpcMemory(models.Model):
    """
    A single conversation exchange between an NPC and a speaker.

    Stores both the raw text and an optional embedding vector (as binary
    blob) for semantic search. The ``npc_name`` and ``speaker_name``
    fields enable matching across game DB wipes where Evennia object IDs
    change — search falls back to name-based matching when ID-based
    returns nothing.
    """

    npc_id = models.IntegerField(db_index=True)
    speaker_id = models.IntegerField(db_index=True)
    speaker_name = models.CharField(max_length=80)
    npc_name = models.CharField(max_length=80)
    user_message = models.TextField()
    assistant_message = models.TextField()
    summary = models.TextField(blank=True, default="")
    embedding = models.BinaryField(null=True, blank=True)
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
