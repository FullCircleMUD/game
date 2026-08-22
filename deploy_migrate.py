"""
Deploy migration script — run by hand on the server before the first
`evennia start` against a new database.

    python deploy_migrate.py

Runs Django migrations directly, bypassing Evennia's launcher. When
DATABASE_URL is set, all database aliases share one Postgres instance
and the routers are off, so a single migrate call handles everything.

Ensures the pgvector extension exists before migrations run, since
ai_memory models depend on the vector type.

Fail-loud semantics:
  - Prints DATABASE_URL presence + the actual DB engine and
    host/name for every alias on startup, so the output shows
    exactly where migrations are going.
  - Any migration error aborts the script with exit code 1 rather
    than leaving you to start the server against a broken database.
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

from server.conf import db_config


def _table_count(alias):
    """How many tables exist in the database behind one alias."""
    conn = connections[alias]
    conn.ensure_connection()
    with conn.cursor() as cursor:
        if "postgresql" in settings.DATABASES[alias].get("ENGINE", ""):
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
            )
        return cursor.fetchone()[0]


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

# Aliases can share one database or sit on separate instances. Anything
# done to a database rather than a table — connect, create extension,
# count tables — happens once per distinct target, using the first alias
# that names it. Anything done to an app's tables happens per alias.
_TARGETS = db_config.distinct_targets(settings.DATABASES)
_REPRESENTATIVES = [aliases[0] for aliases in _TARGETS.values()]
_SPLIT_ALIASES = db_config.split_aliases(settings.DATABASES)

print("Distinct databases behind those aliases:", flush=True)
for _target, _aliases in _TARGETS.items():
    print(f"  {' + '.join(_aliases):<40s} -> {_target[1] or 'local'}"
          f"/{_target[3]}", flush=True)
if _SPLIT_ALIASES:
    print(
        f"\nSplit off from default: {', '.join(_SPLIT_ALIASES)}\n"
        f"  Each needs its own `migrate --database <alias>` — a bare "
        f"migrate cannot reach an alias whose router is active.",
        flush=True,
    )
else:
    print("\nNo alias is split off; one bare migrate covers everything.",
          flush=True)
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

print("--- Probing database connections ---", flush=True)
for _alias in _REPRESENTATIVES:
    _alias_engine = settings.DATABASES[_alias].get("ENGINE", "")
    print(f"  [{_alias}]", flush=True)
    try:
        _conn = connections[_alias]
        _conn.ensure_connection()
        with _conn.cursor() as _cursor:
            if "postgresql" in _alias_engine:
                _cursor.execute(
                    "SELECT current_database(), current_user, version()"
                )
                _db, _user, _version = _cursor.fetchone()
                print(f"    database: {_db}", flush=True)
                print(f"    user:     {_user}", flush=True)
                print(f"    server:   {_version.splitlines()[0]}", flush=True)
            else:
                _cursor.execute("SELECT 1")
                print("    engine:   sqlite (local dev)", flush=True)
        print("    probe:    OK", flush=True)
    except Exception as e:
        print(f"    probe:    FAILED ({e})", flush=True)
        traceback.print_exc()
        print("", flush=True)
        print(
            f"FATAL: could not connect to the database behind '{_alias}'. "
            "Aborting before any migration runs.",
            flush=True,
        )
        sys.exit(1)

print("", flush=True)


# ────────────────────────────────────────────────────────────────────
# pgvector extension (Postgres only)
# ────────────────────────────────────────────────────────────────────

print("--- Ensuring pgvector extension ---", flush=True)
# Extensions are per-database, so this has to run in every database that
# will hold a vector column — not just default's. Lore memory joins this
# tuple when it lands; if it ends up riding the ai_memory alias rather
# than taking its own, there is nothing to add.
_VECTOR_ALIASES = ("ai_memory",)

_vector_databases = {
    alias: settings.DATABASES[alias]
    for alias in _VECTOR_ALIASES
    if alias in settings.DATABASES
}
# One create per distinct database, even if several aliases share it.
_vector_reps = [
    aliases[0]
    for aliases in db_config.distinct_targets(_vector_databases).values()
]

for _alias in _vector_reps:
    if "postgresql" not in settings.DATABASES[_alias].get("ENGINE", ""):
        print(f"  [{_alias}] pgvector: SKIPPED (not Postgres)", flush=True)
        continue
    _db_name = settings.DATABASES[_alias].get("NAME", "?")
    try:
        conn = connections[_alias]
        conn.ensure_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            _present = cursor.fetchone() is not None
    except Exception as e:
        print(f"  [{_alias}] pgvector: CHECK FAILED ({e})", flush=True)
        traceback.print_exc()
        sys.exit(1)

    if _present:
        print(f"  [{_alias}] pgvector: present in {_db_name}", flush=True)
        continue

    # Creating it needs superuser, which the app role deliberately is not.
    # So this reports rather than fixes — with the exact command to run.
    print(f"  [{_alias}] pgvector: MISSING from {_db_name}", flush=True)
    print("", flush=True)
    print(BAR, flush=True)
    print(
        f"FATAL: the '{_alias}' alias resolves to database {_db_name!r}, which\n"
        f"does not have the vector extension. Its migrations create vector\n"
        f"columns and will fail without it.\n"
        f"\n"
        f"Creating an extension requires superuser, which the application role\n"
        f"is not and should not be. Run this as a database superuser, then\n"
        f"re-run this script:\n"
        f"\n"
        f"    sudo -u postgres psql -d {_db_name} -c 'CREATE EXTENSION vector'\n",
        flush=True,
    )
    print(BAR, flush=True)
    sys.exit(1)

print("", flush=True)


# ────────────────────────────────────────────────────────────────────
# Pre-migration table census — so we can tell whether migrations
# are creating tables fresh or targeting an already-populated DB.
# ────────────────────────────────────────────────────────────────────

print("--- Pre-migration table census ---", flush=True)
for _alias in _REPRESENTATIVES:
    try:
        print(
            f"  [{_alias}] tables before migrate: {_table_count(_alias)}",
            flush=True,
        )
    except Exception as e:
        print(f"  [{_alias}] census failed: {e}", flush=True)

print("", flush=True)


# ────────────────────────────────────────────────────────────────────
# Migrations — loud, verbose, fail-hard
# ────────────────────────────────────────────────────────────────────

print("--- Running migrations ---", flush=True)
try:
    # The bare call covers default and every alias sharing its database,
    # because no router stands between them.
    print(">> migrate", flush=True)
    call_command("migrate", verbosity=2, interactive=False)

    # A split alias has an active router, whose allow_migrate() refuses
    # the bare call. Without these it would end up recorded as migrated
    # with none of its tables created.
    for _alias in _SPLIT_ALIASES:
        print("", flush=True)
        print(f">> migrate --database {_alias}", flush=True)
        call_command(
            "migrate", database=_alias, verbosity=2, interactive=False
        )

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
_empty = []
for _alias in _REPRESENTATIVES:
    try:
        _count_after = _table_count(_alias)
        print(
            f"  [{_alias}] tables after migrate: {_count_after}", flush=True
        )
        if _count_after == 0:
            _empty.append(_alias)
    except Exception as e:
        print(f"  [{_alias}] census failed: {e}", flush=True)

# The failure this catches: a router blocks table creation while Django
# still records the migrations as applied, leaving a database that looks
# migrated and holds nothing.
if _empty:
    print("", flush=True)
    print(BAR, flush=True)
    print(
        "FATAL: migrate reported success but these databases have zero "
        f"tables: {', '.join(_empty)}. Something is very wrong — aborting "
        "deploy.",
        flush=True,
    )
    print(BAR, flush=True)
    sys.exit(1)

print("", flush=True)
print(BAR, flush=True)
print("deploy_migrate.py — done", flush=True)
print(BAR, flush=True)
