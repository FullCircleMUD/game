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


# ── Lore Memory ──────────────────────────────────────────────────────


def _build_lore_scope_filter(npc_scope_tags):
    """
    Build a Q filter for lore entries accessible to an NPC.

    Continental entries are always included. For each tag in
    ``npc_scope_tags``, entries whose ``scope_tags`` JSON list contains
    that tag are included. Uses ``__contains`` which works on both
    SQLite and PostgreSQL.

    This is a **permissive pre-filter** — it may include entries the
    NPC shouldn't see (multi-tag entries where the NPC only has one of
    the tags). Use ``_npc_can_access_lore()`` to post-filter results.
    """
    from django.db.models import Q

    q = Q(scope_level="continental")
    for tag in npc_scope_tags:
        q |= Q(scope_tags__contains=[tag])
    return q


def _npc_can_access_lore(entry_scope_tags, npc_scope_tags):
    """
    Check if an NPC can access a lore entry.

    An entry with multiple scope tags (e.g. ``["thieves_guild", "millholm"]``)
    requires the NPC to have **all** of those tags. This prevents a thief
    in another city from knowing Millholm-specific guild secrets, and
    prevents a Millholm townsperson from knowing guild secrets.

    Continental entries (empty scope_tags) are always accessible.
    """
    if not entry_scope_tags:
        return True  # continental — no tags to check
    npc_set = set(npc_scope_tags)
    return all(tag in npc_set for tag in entry_scope_tags)


def store_lore(title, content, scope_level, scope_tags, source=""):
    """
    Store or update a lore entry with embedding.

    Idempotent — matched on ``(source, title)``. If content has changed,
    the embedding is regenerated. If unchanged, the entry is skipped.

    Args:
        title: Human-readable label for the lore entry
        content: The lore text (also used as embedding source)
        scope_level: ``"continental"``, ``"regional"``, ``"local"``, ``"faction"``
        scope_tags: List of scope tags, e.g. ``["millholm"]`` or ``["mages_guild"]``
        source: Provenance string, e.g. ``"millholm/regional.yaml"``

    Returns:
        Tuple of (LoreMemory instance, status) where status is
        ``"created"``, ``"updated"``, or ``"unchanged"``.
    """
    from ai_memory.models import LoreMemory

    # Check for existing entry
    try:
        existing = LoreMemory.objects.using("ai_memory").get(
            source=source, title=title
        )
    except LoreMemory.DoesNotExist:
        existing = None

    # Skip if content and scope unchanged
    if (
        existing
        and existing.content == content
        and existing.scope_level == scope_level
        and existing.scope_tags == scope_tags
    ):
        return existing, "unchanged"

    # Generate embedding
    embedding_raw = None
    try:
        from llm.service import LLMService

        embedding_raw = LLMService.create_embedding(content)
    except Exception:
        logger.exception("Failed to generate embedding for lore: %s", title)

    embedding_bytes = None
    embedding_vector = None
    if embedding_raw is not None:
        if _is_postgres():
            embedding_vector = embedding_raw
        else:
            embedding_bytes = np.asarray(embedding_raw, dtype=np.float32).tobytes()

    if existing:
        existing.content = content
        existing.scope_level = scope_level
        existing.scope_tags = scope_tags
        existing.embedding = embedding_bytes
        existing.embedding_vector = embedding_vector
        existing.save(using="ai_memory")
        return existing, "updated"

    try:
        entry = LoreMemory.objects.using("ai_memory").create(
            title=title,
            content=content,
            scope_level=scope_level,
            scope_tags=scope_tags,
            embedding=embedding_bytes,
            embedding_vector=embedding_vector,
            source=source,
        )
        return entry, "created"
    except Exception:
        logger.exception("Failed to store lore: %s", title)
        return None, "failed"


def search_lore(query_text, npc_scope_tags, top_k=3):
    """
    Semantic search for lore entries accessible to an NPC.

    Filters by scope (continental + matching tags), then ranks by
    cosine similarity to the query. Uses pgvector on PostgreSQL,
    numpy on SQLite.

    Args:
        query_text: The player's message to search against
        npc_scope_tags: List of tags from the NPC's scope resolution
        top_k: Number of results to return

    Returns:
        List of dicts with keys: title, content, scope_level, similarity
    """
    from ai_memory.models import LoreMemory

    # Generate query embedding
    try:
        from llm.service import LLMService

        query_embedding = LLMService.create_embedding(query_text)
    except Exception:
        logger.exception("Failed to embed query for lore search")
        query_embedding = None

    if query_embedding is None:
        return get_recent_lore(npc_scope_tags, limit=top_k)

    scope_filter = _build_lore_scope_filter(npc_scope_tags)
    qs = LoreMemory.objects.using("ai_memory").filter(scope_filter)

    if _is_postgres():
        return _search_lore_pgvector(qs, query_embedding, top_k, npc_scope_tags)
    return _search_lore_numpy(qs, query_embedding, top_k, npc_scope_tags)


def _search_lore_pgvector(qs, query_embedding, top_k, npc_scope_tags):
    """Lore search using pgvector CosineDistance."""
    from pgvector.django import CosineDistance

    # Fetch more than top_k to allow for post-filter dropping some
    qs = (
        qs.filter(embedding_vector__isnull=False)
        .annotate(distance=CosineDistance("embedding_vector", query_embedding))
        .order_by("distance")[:top_k * 3]
    )

    results = []
    for entry in qs:
        if not _npc_can_access_lore(entry.scope_tags, npc_scope_tags):
            continue
        results.append({
            "title": entry.title,
            "content": entry.content,
            "scope_level": entry.scope_level,
            "similarity": 1.0 - entry.distance,
        })
        if len(results) >= top_k:
            break
    return results


def _search_lore_numpy(qs, query_embedding, top_k, npc_scope_tags):
    """Lore search using numpy cosine similarity (SQLite path)."""
    query_vec = np.asarray(query_embedding, dtype=np.float32)

    scored = []
    for entry in qs.iterator():
        if not _npc_can_access_lore(entry.scope_tags, npc_scope_tags):
            continue
        if not entry.embedding:
            continue
        entry_vec = np.frombuffer(bytes(entry.embedding), dtype=np.float32)
        if entry_vec.shape != query_vec.shape:
            continue
        sim = _cosine_similarity(query_vec, entry_vec)
        scored.append((sim, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for sim, entry in scored[:top_k]:
        results.append({
            "title": entry.title,
            "content": entry.content,
            "scope_level": entry.scope_level,
            "similarity": sim,
        })
    return results


def get_recent_lore(npc_scope_tags, limit=3):
    """
    Return the most recent lore entries for an NPC's scope.

    Fallback when semantic search is unavailable (no embedding).

    Returns:
        List of dicts with keys: title, content, scope_level
    """
    from ai_memory.models import LoreMemory

    scope_filter = _build_lore_scope_filter(npc_scope_tags)
    entries = (
        LoreMemory.objects.using("ai_memory")
        .filter(scope_filter)
        .order_by("-updated_at")[:limit * 3]
    )

    results = []
    for entry in entries:
        if not _npc_can_access_lore(entry.scope_tags, npc_scope_tags):
            continue
        results.append({
            "title": entry.title,
            "content": entry.content,
            "scope_level": entry.scope_level,
        })
        if len(results) >= limit:
            break
    return results
