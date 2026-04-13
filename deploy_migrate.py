"""
Railway deploy migration script.

Runs Django migrations directly, bypassing Evennia's launcher. On
Railway all database aliases share one Postgres instance, so a single
migrate call (with no routers) handles everything.

Ensures the pgvector extension exists before migrations run, since
ai_memory models depend on the vector type.

Called from railway.toml startCommand before `evennia start`.

Fail-loud semantics:
  - Prints DATABASE_URL presence + the actual DB engine and
    host/name for every alias on startup, so Railway logs show
    exactly where migrations are going.
  - Any migration error aborts the script with exit code 1 so
    Railway marks the deploy as failed instead of quietly starting
    the server against a broken database.
"""

import os
import sys
import traceback


BAR = "=" * 72

print(BAR, flush=True)
print("deploy_migrate.py — startup", flush=True)
print(BAR, flush=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django
django.setup()

from django.conf import settings
from django.db import connections
from django.core.management import call_command


# ────────────────────────────────────────────────────────────────────
# Environment + DB diagnostics
# ────────────────────────────────────────────────────────────────────

_database_url = os.environ.get("DATABASE_URL")
print(f"DATABASE_URL present: {bool(_database_url)}", flush=True)
if _database_url:
    # Print scheme + host/port/path only — never credentials.
    try:
        from urllib.parse import urlparse
        _parsed = urlparse(_database_url)
        _safe = (
            f"{_parsed.scheme}://{_parsed.hostname or '?'}"
            f":{_parsed.port or '?'}{_parsed.path or ''}"
        )
        print(f"DATABASE_URL target:  {_safe}", flush=True)
    except Exception as _err:
        print(f"DATABASE_URL target:  (unparseable: {_err})", flush=True)

print("", flush=True)
print("Configured databases (from settings.DATABASES):", flush=True)
for _alias in sorted(settings.DATABASES.keys()):
    _cfg = settings.DATABASES[_alias]
    _engine = _cfg.get("ENGINE", "?")
    _name = _cfg.get("NAME", "?")
    _host = _cfg.get("HOST") or "(default)"
    _port = _cfg.get("PORT") or "(default)"
    print(
        f"  [{_alias:<14s}] engine={_engine}  host={_host}  "
        f"port={_port}  name={_name}",
        flush=True,
    )
print("", flush=True)

_default_engine = settings.DATABASES["default"].get("ENGINE", "")
_is_postgres = "postgresql" in _default_engine

# Hard gate: if DATABASE_URL is set but settings didn't apply Postgres,
# that's a bug in settings.py we need to know about immediately.
if _database_url and not _is_postgres:
    print(BAR, flush=True)
    print(
        f"FATAL: DATABASE_URL is set but default DB engine resolved to "
        f"{_default_engine!r}. Check settings.py DATABASE_URL handling — "
        "the Postgres branch never fired.",
        flush=True,
    )
    print(BAR, flush=True)
    sys.exit(1)


# ────────────────────────────────────────────────────────────────────
# Connection probe — ping the default DB before we do anything else
# ────────────────────────────────────────────────────────────────────

print("--- Probing default DB connection ---", flush=True)
try:
    _conn = connections["default"]
    _conn.ensure_connection()
    with _conn.cursor() as _cursor:
        if _is_postgres:
            _cursor.execute(
                "SELECT current_database(), current_user, version()"
            )
            _db, _user, _version = _cursor.fetchone()
            print(f"  database: {_db}", flush=True)
            print(f"  user:     {_user}", flush=True)
            print(f"  server:   {_version.splitlines()[0]}", flush=True)
        else:
            _cursor.execute("SELECT 1")
            print("  engine:   sqlite (local dev)", flush=True)
    print("  probe:    OK", flush=True)
except Exception as e:
    print(f"  probe:    FAILED ({e})", flush=True)
    traceback.print_exc()
    print("", flush=True)
    print("FATAL: could not connect to the default database.", flush=True)
    sys.exit(1)

print("", flush=True)


# ────────────────────────────────────────────────────────────────────
# pgvector extension (Postgres only)
# ────────────────────────────────────────────────────────────────────

print("--- Ensuring pgvector extension ---", flush=True)
if _is_postgres:
    try:
        conn = connections["default"]
        conn.ensure_connection()
        conn.connection.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.connection.autocommit = False
        conn.close()
        print("  pgvector: OK", flush=True)
    except Exception as e:
        print(f"  pgvector: FAILED ({e})", flush=True)
        traceback.print_exc()
        print("", flush=True)
        print(
            "FATAL: pgvector extension could not be created. "
            "ai_memory migrations depend on it — aborting deploy.",
            flush=True,
        )
        sys.exit(1)
else:
    print("  pgvector: SKIPPED (not a Postgres backend)", flush=True)

print("", flush=True)


# ────────────────────────────────────────────────────────────────────
# Pre-migration table census — so we can tell whether migrations
# are creating tables fresh or targeting an already-populated DB.
# ────────────────────────────────────────────────────────────────────

print("--- Pre-migration table census ---", flush=True)
try:
    _conn = connections["default"]
    _conn.ensure_connection()
    with _conn.cursor() as _cursor:
        if _is_postgres:
            _cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        else:
            _cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
            )
        _count = _cursor.fetchone()[0]
    print(f"  tables in default DB before migrate: {_count}", flush=True)
except Exception as e:
    print(f"  census failed: {e}", flush=True)

print("", flush=True)


# ────────────────────────────────────────────────────────────────────
# Migrations — loud, verbose, fail-hard
# ────────────────────────────────────────────────────────────────────

print("--- Running migrations ---", flush=True)
try:
    call_command("migrate", verbosity=2, interactive=False)
    print("", flush=True)
    print("--- Migrations complete ---", flush=True)
except Exception as e:
    print("", flush=True)
    print(BAR, flush=True)
    print(f"FATAL: migration FAILED: {e}", flush=True)
    print(BAR, flush=True)
    traceback.print_exc()
    print("", flush=True)
    print(
        "Deploy aborted — server will NOT start on a broken database.",
        flush=True,
    )
    sys.exit(1)


# ────────────────────────────────────────────────────────────────────
# Post-migration table census — confirm tables were actually created
# ────────────────────────────────────────────────────────────────────

print("", flush=True)
print("--- Post-migration table census ---", flush=True)
try:
    _conn = connections["default"]
    _conn.ensure_connection()
    with _conn.cursor() as _cursor:
        if _is_postgres:
            _cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        else:
            _cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
            )
        _count_after = _cursor.fetchone()[0]
    print(f"  tables in default DB after migrate: {_count_after}", flush=True)
    if _count_after == 0:
        print("", flush=True)
        print(BAR, flush=True)
        print(
            "FATAL: migrate reported success but the default DB has zero "
            "tables. Something is very wrong — aborting deploy.",
            flush=True,
        )
        print(BAR, flush=True)
        sys.exit(1)
except Exception as e:
    print(f"  census failed: {e}", flush=True)

print("", flush=True)
print(BAR, flush=True)
print("deploy_migrate.py — done", flush=True)
print(BAR, flush=True)
