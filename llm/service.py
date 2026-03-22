"""
LLMService — centralized LLM API client for in-game NPCs.

Mirrors the service pattern from blockchain/xrpl/services/. All methods
are class methods. Import inside calling methods to avoid circular imports.
Single point of integration for all LLM calls in the game server.

Uses OpenRouter (OpenAI SDK with custom base_url) — same approach as
FCM-Virtual-Client. Supports model switching per-NPC.

Rate limiting and cost tracking are module-level singletons — they
survive across calls but reset on server restart.
"""

import logging
import threading
import time
from collections import defaultdict

logger = logging.getLogger("llm.service")

# ── Module-level state (resets on server restart) ─────────────────────

_lock = threading.Lock()

_rate_state = {
    "global_timestamps": [],        # list of float timestamps
    "per_npc": defaultdict(list),   # npc_key -> list of float timestamps
}

_cost_state = {
    "total_cost_cents": 0.0,
    "per_model": defaultdict(float),
    "per_npc": defaultdict(float),
    "total_calls": 0,
    "day_start": 0.0,               # reset daily cost at midnight
}

# Approximate cost per 1K tokens (averaged input/output) by model prefix.
# Used for estimation only — actual billing is on OpenRouter's side.
_MODEL_COST_PER_1K = {
    "openai/gpt-4o-mini": 0.015,
    "openai/gpt-4o": 0.50,
    "anthropic/claude-haiku": 0.025,
    "anthropic/claude-sonnet": 0.30,
    "google/gemini-2.0-flash": 0.01,
}


class LLMService:
    """Centralized service for all LLM API calls in the game."""

    _client = None
    _embedding_client = None

    # ── Public API ────────────────────────────────────────────────────

    @classmethod
    def chat_completion(
        cls,
        messages,
        model=None,
        max_tokens=150,
        temperature=0.8,
        npc_key=None,
    ):
        """
        Send a chat completion request to OpenRouter.

        This is a SYNCHRONOUS call. The caller (LLMMixin) is responsible
        for wrapping it in ``deferToThread`` so it doesn't block the
        Twisted reactor.

        Args:
            messages: list of {"role": str, "content": str}
            model: OpenRouter model string (defaults to settings.LLM_DEFAULT_MODEL)
            max_tokens: response length cap
            temperature: creativity 0.0-1.0
            npc_key: unique identifier for per-NPC rate limiting (e.g. dbref)

        Returns:
            str: The assistant's response text, or None if rate-limited/failed.
        """
        from django.conf import settings

        if not getattr(settings, "LLM_ENABLED", True):
            return None

        model = model or getattr(settings, "LLM_DEFAULT_MODEL", "openai/gpt-4o-mini")

        # Rate limit check
        if not cls._check_rate_limit(npc_key):
            logger.debug("Rate limited: npc_key=%s", npc_key)
            return None

        # Daily cost cap check
        if cls._is_over_daily_cap():
            logger.warning("Daily LLM cost cap exceeded — all calls disabled")
            return None

        try:
            client = cls._get_client()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            content = response.choices[0].message.content

            # Track cost
            usage = response.usage
            if usage:
                cls._track_cost(
                    model,
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    npc_key,
                )

            logger.debug(
                "LLM call: model=%s npc=%s tokens=%s/%s",
                model,
                npc_key,
                usage.prompt_tokens if usage else "?",
                usage.completion_tokens if usage else "?",
            )

            return content

        except Exception:
            logger.exception("LLM API call failed for npc_key=%s", npc_key)
            return None

    @classmethod
    def create_embedding(cls, text, model=None):
        """
        Generate an embedding vector for the given text.

        Uses a separate embedding client that defaults to OpenAI direct
        (since OpenRouter may not support the embeddings endpoint).

        Args:
            text: The text to embed.
            model: Embedding model ID. Defaults to settings.LLM_EMBEDDING_MODEL.

        Returns:
            list[float]: The embedding vector, or None on failure.
        """
        from django.conf import settings

        if not getattr(settings, "LLM_ENABLED", True):
            return None

        model = model or getattr(
            settings, "LLM_EMBEDDING_MODEL", "text-embedding-3-small"
        )

        try:
            client = cls._get_embedding_client()
            response = client.embeddings.create(
                model=model,
                input=text,
            )
            return response.data[0].embedding
        except Exception:
            logger.exception("Embedding API call failed")
            return None

    @classmethod
    def get_cost_report(cls):
        """Return cost tracking summary for admin/debugging."""
        with _lock:
            return {
                "total_cost_cents": round(_cost_state["total_cost_cents"], 4),
                "total_calls": _cost_state["total_calls"],
                "per_model": dict(_cost_state["per_model"]),
                "per_npc": dict(_cost_state["per_npc"]),
            }

    @classmethod
    def reset_cost_tracking(cls):
        """Admin utility: reset all cost tracking."""
        with _lock:
            _cost_state["total_cost_cents"] = 0.0
            _cost_state["per_model"] = defaultdict(float)
            _cost_state["per_npc"] = defaultdict(float)
            _cost_state["total_calls"] = 0
            _cost_state["day_start"] = time.time()

    # ── Internal ──────────────────────────────────────────────────────

    @classmethod
    def _get_client(cls):
        """Lazy-init the OpenAI client pointed at OpenRouter."""
        if cls._client is None:
            from django.conf import settings
            from openai import OpenAI

            api_key = getattr(settings, "LLM_API_KEY", "")
            base_url = getattr(
                settings, "LLM_API_BASE_URL", "https://openrouter.ai/api/v1"
            )
            cls._client = OpenAI(base_url=base_url, api_key=api_key)
        return cls._client

    @classmethod
    def _get_embedding_client(cls):
        """Lazy-init a separate OpenAI client for embeddings.

        Defaults to OpenAI direct (api.openai.com) since OpenRouter
        may not support the embeddings endpoint. Uses LLM_EMBEDDING_API_KEY
        if set, otherwise falls back to LLM_API_KEY.
        """
        if cls._embedding_client is None:
            from django.conf import settings
            from openai import OpenAI

            api_key = getattr(
                settings,
                "LLM_EMBEDDING_API_KEY",
                getattr(settings, "LLM_API_KEY", ""),
            )
            base_url = getattr(
                settings,
                "LLM_EMBEDDING_API_BASE_URL",
                "https://api.openai.com/v1",
            )
            cls._embedding_client = OpenAI(base_url=base_url, api_key=api_key)
        return cls._embedding_client

    @classmethod
    def _check_rate_limit(cls, npc_key=None):
        """
        Sliding-window rate limit check.

        Returns True if the request is allowed, False if rate-limited.
        """
        from django.conf import settings

        now = time.time()
        window = 60.0  # 1-minute sliding window

        global_max = getattr(settings, "LLM_GLOBAL_MAX_CALLS_PER_MINUTE", 60)
        per_npc_max = getattr(settings, "LLM_PER_NPC_MAX_CALLS_PER_MINUTE", 6)

        with _lock:
            # Global limit
            timestamps = _rate_state["global_timestamps"]
            timestamps[:] = [t for t in timestamps if now - t < window]
            if len(timestamps) >= global_max:
                return False

            # Per-NPC limit
            if npc_key:
                npc_ts = _rate_state["per_npc"][npc_key]
                npc_ts[:] = [t for t in npc_ts if now - t < window]
                if len(npc_ts) >= per_npc_max:
                    return False
                npc_ts.append(now)

            timestamps.append(now)

        return True

    @classmethod
    def _is_over_daily_cap(cls):
        """Check if daily cost cap has been exceeded."""
        from django.conf import settings

        cap = getattr(settings, "LLM_DAILY_COST_LIMIT_CENTS", 500)
        now = time.time()

        with _lock:
            # Reset daily counter at midnight (roughly every 24h)
            if now - _cost_state["day_start"] > 86400:
                _cost_state["total_cost_cents"] = 0.0
                _cost_state["day_start"] = now

            return _cost_state["total_cost_cents"] >= cap

    @classmethod
    def _track_cost(cls, model, prompt_tokens, completion_tokens, npc_key):
        """Accumulate estimated cost for monitoring."""
        total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

        # Find best matching cost rate
        cost_per_1k = 0.015  # default (gpt-4o-mini rate)
        for prefix, rate in _MODEL_COST_PER_1K.items():
            if model.startswith(prefix):
                cost_per_1k = rate
                break

        cost_cents = (total_tokens / 1000.0) * cost_per_1k

        with _lock:
            _cost_state["total_cost_cents"] += cost_cents
            _cost_state["total_calls"] += 1
            _cost_state["per_model"][model] += cost_cents
            if npc_key:
                _cost_state["per_npc"][npc_key] += cost_cents
