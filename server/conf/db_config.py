"""
Connection resolution for the database aliases.

Lives outside settings.py so the logic is directly unit-testable and the
settings module stays declarative. See tests/test_db_config.py for the
scenarios these are expected to produce, and design/database.md for the
architecture they implement.

Every function here takes what it needs as arguments and reads nothing
from the process environment or from Django settings, so a test can name
an environment without touching the real one.
"""

import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured


# Persistent connections. Postgres only — SQLite reconnects are free and
# holding the file open across requests buys nothing.
CONN_MAX_AGE = 600

# An omitted port and an explicitly-stated default port name the same
# server, but dj_database_url leaves PORT empty for the first and set for
# the second. Filling in the default before comparing means a URL can be
# spelled either way without inventing a spurious router.
DEFAULT_PORTS = {
    "django.db.backends.postgresql": "5432",
    "django.db.backends.mysql": "3306",
    "django.db.backends.oracle": "1521",
}

# Session parameters set on every Postgres connection.
#
# hnsw.iterative_scan — a filtered vector search (``WHERE npc_id = X ORDER
# BY embedding <=> ...``) asks HNSW for ef_search candidates and only then
# applies the filter, so it returns whatever few of them survive. Measured
# on 100k rows across 500 NPCs: 1 row returned of a requested 5. Iterative
# scans keep pulling candidates until the filter yields enough.
#
# Set on the connection rather than in postgresql.conf so it follows the
# database wherever it lands — an RDS instance has no postgresql.conf to
# edit, only a parameter group to forget. Postgres accepts the setting on
# databases where the vector extension is absent, so it is safe on every
# alias rather than needing to track which one holds the embeddings.
SESSION_OPTIONS = "-c hnsw.iterative_scan=relaxed_order"


def resolve_database(alias, sqlite_filename, game_dir, env):
    """Build the connection config for one database alias.

    Resolution order:

      1. ``DATABASE_URL_<ALIAS>``  this alias has its own Postgres instance
      2. ``DATABASE_URL``          share the default's Postgres instance
      3. SQLite file               local dev, one file per alias

    Args:
        alias (str): the Django database alias, e.g. ``"ai_memory"``.
        sqlite_filename (str): file to fall back to under ``<game_dir>/server/``.
        game_dir (str): the Evennia game directory.
        env (Mapping): environment variables to read, normally ``os.environ``.

    Returns:
        dict: a Django DATABASES entry.
    """
    source = f"DATABASE_URL_{alias.upper()}"
    url = env.get(source)
    if not url:
        source, url = "DATABASE_URL", env.get("DATABASE_URL")
    if url:
        config = dj_database_url.parse(url)
        _reject_incomplete_url(config, source)
        config["CONN_MAX_AGE"] = CONN_MAX_AGE
        apply_session_options(config)
        return config
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(game_dir, "server", sqlite_filename),
    }


def apply_session_options(config):
    """Add SESSION_OPTIONS to a Postgres connection, keeping anything already there.

    A no-op on non-Postgres backends, where ``OPTIONS`` means something
    entirely different and a libpq string would break the connection.

    Args:
        config (dict): a Django DATABASES entry, modified in place.
    """
    if "postgresql" not in config.get("ENGINE", ""):
        return
    options = config.setdefault("OPTIONS", {})
    existing = str(options.get("options", "")).strip()
    options["options"] = f"{existing} {SESSION_OPTIONS}".strip()


def _reject_incomplete_url(config, source):
    """Refuse to start on a URL that names a server without saying which.

    A URL missing its host or database name parses without complaint and
    then silently fails to match `default`'s target, which manufactures a
    router and leaves that alias's tables uncreated. Cheaper to refuse at
    settings load than to debug an empty database later.

    Args:
        config (dict): the parsed DATABASES entry.
        source (str): the environment variable it came from, for the message.

    Raises:
        ImproperlyConfigured: if a network database omits host or name.
    """
    if "sqlite" in config.get("ENGINE", ""):
        return  # File-based — there is no host or port to get wrong.
    missing = [key for key in ("HOST", "NAME") if not config.get(key)]
    if missing:
        raise ImproperlyConfigured(
            f"{source} is missing {' and '.join(m.lower() for m in missing)}. "
            f"Give it the full form — postgres://user:pass@host:port/dbname — "
            f"so it can be matched against the other database aliases."
        )


def database_target(config):
    """Identify the physical database a connection config points at.

    Two aliases sharing a target are the same database and must not have
    a router between them. Compared instead of the URL string, because
    one database can be spelled more than one way.

    An omitted port is filled in from DEFAULT_PORTS so the two spellings
    of the same server match. Host spelling is NOT normalised — naming
    one alias `localhost` and another `127.0.0.1` will read as two
    databases. Deciding otherwise would mean resolving names at settings
    load, so use the same host string across the aliases.

    Args:
        config (dict): a Django DATABASES entry.

    Returns:
        tuple: engine, host, port, name — normalised to strings so a
            missing key and an empty one compare equal.
    """
    engine = config.get("ENGINE", "")
    return (
        engine,
        config.get("HOST") or "",
        str(config.get("PORT") or "") or DEFAULT_PORTS.get(engine, ""),
        config.get("NAME", ""),
    )


def split_aliases(databases):
    """The aliases living on a physically different database from ``default``.

    The single definition of "this alias has been split off", used both to
    decide which routers to run and which aliases need their own migrate
    call. Deriving both from one function is what stops the two drifting
    into a state where a router blocks a table that nothing else creates.

    Args:
        databases (dict): resolved Django DATABASES, including ``default``.

    Returns:
        list: alias names, in ``databases`` order, excluding ``default``.
    """
    default_target = database_target(databases["default"])
    return [
        alias
        for alias, config in databases.items()
        if alias != "default" and database_target(config) != default_target
    ]


def active_routers(databases, router_paths):
    """Select the routers Django should run, given the resolved connections.

    A router is needed for exactly the split aliases. Both existing
    deployment modes fall out of that rule with nothing to configure:
    locally every alias is its own SQLite file, so all routers are
    active; on one shared Postgres instance every alias is the same
    database, so none are.

    Enabling a router in the shared case would be actively harmful — its
    ``allow_migrate()`` would refuse to create the non-default tables
    while Django still recorded those migrations as applied, leaving a
    database that looks migrated and has no tables.

    The corollary: an alias with an active router is not reached by a
    bare ``migrate`` and needs ``migrate --database <alias>``.

    Args:
        databases (dict): resolved Django DATABASES, including ``default``.
        router_paths (dict): alias -> dotted path of the router serving it.

    Returns:
        list: dotted router paths, in ``router_paths`` order.
    """
    split = set(split_aliases(databases))
    return [path for alias, path in router_paths.items() if alias in split]


def distinct_targets(databases):
    """Group the aliases by the physical database they share.

    Anything done to a database rather than to a table — connecting,
    creating an extension, counting what is in there — has to be done
    once per distinct database, not once per alias.

    Args:
        databases (dict): resolved Django DATABASES.

    Returns:
        dict: target tuple -> list of aliases sharing it, first-seen order.
    """
    grouped = {}
    for alias, config in databases.items():
        grouped.setdefault(database_target(config), []).append(alias)
    return grouped
