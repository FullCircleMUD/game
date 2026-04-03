"""
AI Memory services — store, search, and retrieve NPC memories.

All functions are synchronous. The caller (LLMMixin) wraps them in
``deferToThread`` so they don't block the Twisted reactor.

Dual backend:
  - **PostgreSQL** (Railway): uses pgvector ``<=>`` operator with HNSW
    index for sub-linear cosine similarity search.
  - **SQLite** (local dev): uses numpy cosine similarity in a Python
    loop (unchanged from Phase 1).

Backend is detected automatically from
``settings.DATABASES["ai_memory"]["ENGINE"]``.
"""

import logging
import time

import numpy as np
from django.utils import timezone

logger = logging.getLogger("ai_memory.services")


# ── Backend Detection ────────────────────────────────────────────────


def _is_postgres():
    """Return True if the ai_memory database is PostgreSQL."""
    from django.conf import settings

    engine = settings.DATABASES.get("ai_memory", {}).get("ENGINE", "")
    return "postgresql" in engine


# ── Cosine Similarity (SQLite path only) ─────────────────────────────


def _cosine_similarity(a, b):
    """Cosine similarity between two numpy vectors."""
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm < 1e-8:
        return 0.0
    return float(dot / norm)


# ── Time Formatting ──────────────────────────────────────────────────


def _time_ago_str(dt):
    """
    Human-readable relative time for NPC dialogue context.

    Returns natural language strings like "a few minutes ago",
    "yesterday", "back in December", "over a year ago".
    """
    now = timezone.now()
    delta = now - dt
    seconds = delta.total_seconds()

    if seconds < 3600:          # < 1 hour
        return "a few minutes ago"
    if seconds < 86400:         # < 24 hours
        return "earlier today"
    if seconds < 172800:        # < 48 hours
        return "yesterday"
    if seconds < 604800:        # < 7 days
        return "a few days ago"
    if seconds < 2592000:       # < 30 days
        return "a couple of weeks ago"
    if seconds < 31536000:      # < 365 days
        return f"back in {dt.strftime('%B')}"
    return "over a year ago"


# ── Store ────────────────────────────────────────────────────────────


def store_memory(npc, speaker, user_msg, assistant_msg, interaction_type="say"):
    """
    Store a conversation exchange with embedding in the ai_memory database.

    Args:
        npc: The NPC object (has .id, .key)
        speaker: The speaker object (has .id, .key)
        user_msg: What the speaker said
        assistant_msg: What the NPC replied
        interaction_type: "say", "whisper", "arrive", "leave"
    """
    from ai_memory.models import NpcMemory

    summary = f'{speaker.key} said: "{user_msg}" | {npc.key} replied: "{assistant_msg}"'

    # Generate embedding
    embedding_raw = None
    try:
        from llm.service import LLMService

        embedding_raw = LLMService.create_embedding(summary)
    except Exception:
        logger.exception("Failed to generate embedding for NPC %s", npc.key)

    # Prepare backend-specific fields
    embedding_bytes = None
    embedding_vector = None

    if embedding_raw is not None:
        if _is_postgres():
            embedding_vector = embedding_raw  # list[float] → pgvector
        else:
            embedding_bytes = np.asarray(embedding_raw, dtype=np.float32).tobytes()

    try:
        NpcMemory.objects.using("ai_memory").create(
            npc_id=npc.id,
            speaker_id=speaker.id,
            speaker_name=speaker.key,
            npc_name=npc.key,
            user_message=user_msg,
            assistant_message=assistant_msg,
            summary=summary,
            embedding=embedding_bytes,
            embedding_vector=embedding_vector,
            interaction_type=interaction_type,
        )
    except Exception:
        logger.exception("Failed to store memory for NPC %s", npc.key)


# ── Search (Semantic) ────────────────────────────────────────────────


def search_memories(npc_id, query_text, top_k=5, speaker_id=None, npc_name=None):
    """
    Find the most relevant memories for a query using cosine similarity.

    Falls back to name-based matching if npc_id returns no results
    (handles game DB wipes where Evennia object IDs change).

    On PostgreSQL, uses pgvector's ``CosineDistance`` with HNSW index.
    On SQLite, uses the numpy cosine similarity loop.

    Args:
        npc_id: The NPC's Evennia object ID
        query_text: The text to search for semantically
        top_k: Number of results to return
        speaker_id: Optional filter to a specific speaker
        npc_name: NPC name for fallback matching after DB wipes

    Returns:
        List of dicts with keys: summary, user_message, assistant_message,
        similarity, created_at, time_ago, speaker_name
    """
    from ai_memory.models import NpcMemory

    # Generate query embedding
    try:
        from llm.service import LLMService

        query_embedding = LLMService.create_embedding(query_text)
    except Exception:
        logger.exception("Failed to embed query for search")
        query_embedding = None

    if query_embedding is None:
        # Can't do semantic search without embedding — fall back to recent
        return get_recent_memories(npc_id, limit=top_k, npc_name=npc_name)

    if _is_postgres():
        return _search_memories_pgvector(
            npc_id, query_embedding, top_k, speaker_id, npc_name
        )
    return _search_memories_numpy(
        npc_id, query_embedding, top_k, speaker_id, npc_name
    )


def _build_search_queryset(npc_id, speaker_id, npc_name):
    """Build the base queryset for memory search with ID/name fallback."""
    from ai_memory.models import NpcMemory

    qs = NpcMemory.objects.using("ai_memory").filter(npc_id=npc_id)
    if speaker_id:
        qs = qs.filter(speaker_id=speaker_id)

    if not qs.exists() and npc_name:
        qs = NpcMemory.objects.using("ai_memory").filter(npc_name=npc_name)
        if speaker_id:
            qs = qs.filter(speaker_id=speaker_id)

    return qs


def _search_memories_pgvector(npc_id, query_embedding, top_k, speaker_id, npc_name):
    """
    Semantic search using pgvector CosineDistance — single SQL query,
    HNSW index-backed.
    """
    from pgvector.django import CosineDistance

    qs = _build_search_queryset(npc_id, speaker_id, npc_name)
    qs = (
        qs.filter(embedding_vector__isnull=False)
        .annotate(distance=CosineDistance("embedding_vector", query_embedding))
        .order_by("distance")[:top_k]
    )

    results = []
    for mem in qs:
        results.append({
            "summary": mem.summary,
            "user_message": mem.user_message,
            "assistant_message": mem.assistant_message,
            "similarity": 1.0 - mem.distance,
            "created_at": mem.created_at,
            "time_ago": _time_ago_str(mem.created_at),
            "speaker_name": mem.speaker_name,
        })

    return results


def _search_memories_numpy(npc_id, query_embedding, top_k, speaker_id, npc_name):
    """
    Semantic search using numpy cosine similarity — O(n) Python loop.
    Used on SQLite (local dev).
    """
    query_vec = np.asarray(query_embedding, dtype=np.float32)
    qs = _build_search_queryset(npc_id, speaker_id, npc_name)

    # Score each memory by cosine similarity
    scored = []
    for mem in qs.iterator():
        if not mem.embedding:
            continue
        mem_vec = np.frombuffer(bytes(mem.embedding), dtype=np.float32)
        if mem_vec.shape != query_vec.shape:
            continue
        sim = _cosine_similarity(query_vec, mem_vec)
        scored.append((sim, mem))

    # Sort by similarity descending, take top_k
    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for sim, mem in scored[:top_k]:
        results.append({
            "summary": mem.summary,
            "user_message": mem.user_message,
            "assistant_message": mem.assistant_message,
            "similarity": sim,
            "created_at": mem.created_at,
            "time_ago": _time_ago_str(mem.created_at),
            "speaker_name": mem.speaker_name,
        })

    return results


# ── Recent Memories (Fallback) ───────────────────────────────────────


def get_recent_memories(npc_id, limit=10, npc_name=None):
    """
    Return the most recent memories — no embedding needed.

    Falls back to name-based matching if npc_id returns no results.

    Returns:
        List of dicts with keys: summary, user_message, assistant_message,
        created_at, time_ago, speaker_name
    """
    from ai_memory.models import NpcMemory

    qs = NpcMemory.objects.using("ai_memory").filter(npc_id=npc_id)

    if not qs.exists() and npc_name:
        qs = NpcMemory.objects.using("ai_memory").filter(npc_name=npc_name)

    memories = qs.order_by("-created_at")[:limit]

    results = []
    for mem in memories:
        results.append({
            "summary": mem.summary,
            "user_message": mem.user_message,
            "assistant_message": mem.assistant_message,
            "created_at": mem.created_at,
            "time_ago": _time_ago_str(mem.created_at),
            "speaker_name": mem.speaker_name,
        })

    # Return in chronological order (oldest first) for prompt context
    results.reverse()
    return results


# ── Last Interaction Time ────────────────────────────────────────────


def get_last_interaction_time(npc_id, speaker_id, npc_name=None, speaker_name=None):
    """
    Return the datetime of the most recent memory with a specific speaker.

    Falls back to name-based matching if ID-based returns nothing.

    Returns:
        Tuple of (datetime, time_ago_str) or (None, None) if no history.
    """
    from ai_memory.models import NpcMemory

    qs = NpcMemory.objects.using("ai_memory").filter(
        npc_id=npc_id, speaker_id=speaker_id
    )

    if not qs.exists() and npc_name and speaker_name:
        qs = NpcMemory.objects.using("ai_memory").filter(
            npc_name=npc_name, speaker_name=speaker_name
        )

    last = qs.order_by("-created_at").first()
    if last:
        return last.created_at, _time_ago_str(last.created_at)
    return None, None
