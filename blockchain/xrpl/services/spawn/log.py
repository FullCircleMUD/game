"""
Logging for the unified spawn system.

One helper, ``spawn_log(message, level="INFO")``, routing a line into
``spawn.log`` beside Evennia's own logs in ``settings.LOG_DIR``.

Why a dedicated file rather than the stdlib logger:

- **Thread safety.** A tick runs in a worker thread via ``deferToThread``.
  Evennia's ``log_file`` dispatches through its own thread pool, so worker
  threads can call it without locking concerns.
- **One narrative across processes.** Under sharding the router decides and a
  shard places. Both write here, each line tagged with which process wrote
  it, so a placement can be followed end to end in a single ``tail``.
- **No stdlib logging hierarchy.** ``logging.getLogger("evennia")`` returns a
  plain ``Logger``, which has no ``log_trace`` — calling it raises
  ``AttributeError`` from inside an ``except`` block and destroys the
  original error. Routing through Evennia's own surface avoids that class of
  problem entirely.

Line format:

    <ISO-8601 timestamp> [<LEVEL>] [<process>] <message>

for example::

    2026-08-04T10:15:02+00:00 [INFO] [router] plan resources/1: 4 targets, ...
    2026-08-04T10:15:03+00:00 [INFO] [shard0] place resources/1 x4 on 3308

Levels are ``INFO``, ``WARN`` and ``ERROR``. There is deliberately no level
filtering and no verbosity setting: the system is logged heavily while it is
being brought up, and noisy call sites get removed once it is stable, rather
than being silenced at runtime.

Outside a running Evennia engine — unit tests, any future CLI — this is a
silent no-op. A log call must never raise into its caller, so every failure
path here degrades to doing nothing.
"""

from datetime import datetime, timezone

_LOG_FILENAME = "spawn.log"
_VALID_LEVELS = ("INFO", "WARN", "ERROR")


def _process_tag():
    """Identify the writing process: 'router', a shard id, or 'monolith'.

    Never raises — an unidentifiable process logs as 'unknown' rather than
    breaking the call site it was meant to be reporting on.
    """
    try:
        from evennia_shards import ROLE_ROUTER, ROLE_MONOLITH, get_role, get_shard_id

        role = get_role()
        if role == ROLE_ROUTER:
            return "router"
        if role == ROLE_MONOLITH:
            return "monolith"
        return get_shard_id() or "shard"
    except Exception:
        # evennia_shards absent (monolith without the library installed) or
        # settings not yet loaded.
        return "monolith"


def spawn_log(message, level="INFO"):
    """Emit one line to ``spawn.log``.

    ``level`` is coerced to ``INFO`` if unrecognised — an odd level should
    not lose the message.
    """
    try:
        from evennia.utils.logger import log_file
    except ImportError:
        return

    if level not in _VALID_LEVELS:
        level = "INFO"

    try:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        log_file(
            f"{timestamp} [{level}] [{_process_tag()}] {message}",
            filename=_LOG_FILENAME,
        )
    except Exception:
        # Logging must never take down the operation it is describing.
        pass
