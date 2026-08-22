"""
Tests for server/conf/db_config.py — how each database alias resolves its
connection, and which routers that resolution implies.

The rule under test: a router is active for exactly those aliases that are
a physically different database from `default`. Getting that wrong in the
permissive direction costs nothing; getting it wrong in the strict
direction manufactures a router, which stops `migrate` creating that
alias's tables while Django still records the migrations as applied.

evennia test --settings settings tests.server_tests.test_db_config
"""

import os
from unittest import TestCase

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from server.conf import db_config


GAME_DIR = os.path.join("/srv", "fcm", "game")

SHARED = "postgres://u:p@db.example.com:5432/fcm"
SHARED_NO_PORT = "postgres://u:p@db.example.com/fcm"
VECTORS = "postgres://u:p@vectors.example.com:5432/ai_memory"

ROUTER_PATHS = {
    "xrpl": "blockchain.xrpl.db_router.XRPLRouter",
    "ai_memory": "ai_memory.db_router.AiMemoryRouter",
    "subscriptions": "subscriptions.db_router.SubscriptionsRouter",
}


def sqlite_at(path):
    return {"ENGINE": "django.db.backends.sqlite3", "NAME": path}


class TestResolveDatabase(TestCase):
    """resolve_database() picks per-alias URL, then shared URL, then SQLite."""

    def resolve(self, env, alias="ai_memory"):
        return db_config.resolve_database(
            alias, f"{alias}.db3", GAME_DIR, env
        )

    def test_no_urls_falls_back_to_a_sqlite_file(self):
        config = self.resolve({})
        self.assertEqual(config["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(
            config["NAME"],
            os.path.join(GAME_DIR, "server", "ai_memory.db3"),
        )

    def test_shared_url_is_used_when_there_is_no_override(self):
        config = self.resolve({"DATABASE_URL": SHARED})
        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["HOST"], "db.example.com")
        self.assertEqual(config["NAME"], "fcm")

    def test_override_beats_the_shared_url(self):
        config = self.resolve(
            {"DATABASE_URL": SHARED, "DATABASE_URL_AI_MEMORY": VECTORS}
        )
        self.assertEqual(config["HOST"], "vectors.example.com")
        self.assertEqual(config["NAME"], "ai_memory")

    def test_override_works_with_no_shared_url_set(self):
        config = self.resolve({"DATABASE_URL_AI_MEMORY": VECTORS})
        self.assertEqual(config["HOST"], "vectors.example.com")

    def test_an_override_for_a_different_alias_is_ignored(self):
        config = self.resolve(
            {"DATABASE_URL": SHARED, "DATABASE_URL_XRPL": VECTORS}
        )
        self.assertEqual(config["HOST"], "db.example.com")

    def test_postgres_connections_are_persistent(self):
        config = self.resolve({"DATABASE_URL": SHARED})
        self.assertEqual(config["CONN_MAX_AGE"], db_config.CONN_MAX_AGE)

    def test_sqlite_gets_no_conn_max_age(self):
        self.assertNotIn("CONN_MAX_AGE", self.resolve({}))


class TestIncompleteUrlsAreRejected(TestCase):
    """A URL that cannot be compared reliably must stop the server, loudly."""

    def resolve(self, env):
        return db_config.resolve_database(
            "ai_memory", "ai_memory.db3", GAME_DIR, env
        )

    def test_override_without_a_database_name_raises(self):
        with self.assertRaises(ImproperlyConfigured) as caught:
            self.resolve({"DATABASE_URL_AI_MEMORY": "postgres://u:p@h:5432"})
        self.assertIn("DATABASE_URL_AI_MEMORY", str(caught.exception))
        self.assertIn("name", str(caught.exception))

    def test_override_without_a_host_raises(self):
        with self.assertRaises(ImproperlyConfigured) as caught:
            self.resolve({"DATABASE_URL_AI_MEMORY": "postgres:///fcm"})
        self.assertIn("host", str(caught.exception))

    def test_the_shared_url_is_named_when_it_is_the_broken_one(self):
        with self.assertRaises(ImproperlyConfigured) as caught:
            self.resolve({"DATABASE_URL": "postgres://u:p@h:5432"})
        self.assertIn("DATABASE_URL", str(caught.exception))

    def test_a_sqlite_url_is_allowed_to_have_no_host(self):
        config = self.resolve({"DATABASE_URL": "sqlite:////tmp/fcm.db3"})
        self.assertIn("sqlite", config["ENGINE"])


class TestDatabaseTarget(TestCase):
    """database_target() decides whether two aliases are the same database."""

    def test_identical_configs_match(self):
        env = {"DATABASE_URL": SHARED}
        left = db_config.resolve_database("xrpl", "x.db3", GAME_DIR, env)
        right = db_config.resolve_database("ai_memory", "a.db3", GAME_DIR, env)
        self.assertEqual(
            db_config.database_target(left), db_config.database_target(right)
        )

    def test_omitted_port_matches_the_explicit_default(self):
        """The trap: postgres://host/db and postgres://host:5432/db are one server."""
        with_port = db_config.resolve_database(
            "xrpl", "x.db3", GAME_DIR, {"DATABASE_URL": SHARED}
        )
        without = db_config.resolve_database(
            "xrpl", "x.db3", GAME_DIR, {"DATABASE_URL": SHARED_NO_PORT}
        )
        self.assertEqual(
            db_config.database_target(with_port),
            db_config.database_target(without),
        )

    def test_a_different_host_is_a_different_database(self):
        left = db_config.resolve_database(
            "xrpl", "x.db3", GAME_DIR, {"DATABASE_URL": SHARED}
        )
        right = db_config.resolve_database(
            "xrpl", "x.db3", GAME_DIR, {"DATABASE_URL": VECTORS}
        )
        self.assertNotEqual(
            db_config.database_target(left), db_config.database_target(right)
        )

    def test_a_different_name_on_the_same_host_is_a_different_database(self):
        same_host_other_db = "postgres://u:p@db.example.com:5432/other"
        left = db_config.resolve_database(
            "xrpl", "x.db3", GAME_DIR, {"DATABASE_URL": SHARED}
        )
        right = db_config.resolve_database(
            "xrpl", "x.db3", GAME_DIR, {"DATABASE_URL": same_host_other_db}
        )
        self.assertNotEqual(
            db_config.database_target(left), db_config.database_target(right)
        )

    def test_absent_keys_and_empty_keys_are_the_same_thing(self):
        bare = {"ENGINE": "django.db.backends.sqlite3", "NAME": "/db3"}
        spelled_out = {**bare, "HOST": "", "PORT": ""}
        self.assertEqual(
            db_config.database_target(bare),
            db_config.database_target(spelled_out),
        )

    def test_separate_sqlite_files_are_separate_databases(self):
        self.assertNotEqual(
            db_config.database_target(sqlite_at("/srv/evennia.db3")),
            db_config.database_target(sqlite_at("/srv/ai_memory.db3")),
        )


class TestActiveRouters(TestCase):
    """active_routers() turns the resolved connections into a router list."""

    def routers(self, env):
        """Resolve all four aliases the way settings.py does, then derive."""
        shared = env.get("DATABASE_URL")
        databases = {
            "default": dj_database_url.parse(shared)
            if shared
            else sqlite_at(os.path.join(GAME_DIR, "server", "evennia.db3"))
        }
        for alias in ROUTER_PATHS:
            databases[alias] = db_config.resolve_database(
                alias, f"{alias}.db3", GAME_DIR, env
            )
        return db_config.active_routers(databases, ROUTER_PATHS)

    def test_local_sqlite_activates_every_router(self):
        """Four separate files, so every alias needs directing to its own."""
        self.assertEqual(self.routers({}), list(ROUTER_PATHS.values()))

    def test_one_shared_postgres_activates_none(self):
        """Same database throughout — a router here would block migrations."""
        self.assertEqual(self.routers({"DATABASE_URL": SHARED}), [])

    def test_one_split_alias_activates_only_its_own_router(self):
        routers = self.routers(
            {"DATABASE_URL": SHARED, "DATABASE_URL_AI_MEMORY": VECTORS}
        )
        self.assertEqual(routers, [ROUTER_PATHS["ai_memory"]])

    def test_two_split_aliases_activate_both_in_declaration_order(self):
        routers = self.routers({
            "DATABASE_URL": SHARED,
            "DATABASE_URL_AI_MEMORY": VECTORS,
            "DATABASE_URL_XRPL": "postgres://u:p@chain.example.com:5432/xrpl",
        })
        self.assertEqual(
            routers, [ROUTER_PATHS["xrpl"], ROUTER_PATHS["ai_memory"]]
        )

    def test_an_override_naming_the_default_database_activates_nothing(self):
        """Pointing an alias back at the shared database is a no-op, not a split."""
        self.assertEqual(
            self.routers(
                {"DATABASE_URL": SHARED, "DATABASE_URL_XRPL": SHARED}
            ),
            [],
        )

    def test_the_same_database_spelled_without_its_port_activates_nothing(self):
        """Regression: a port-only spelling difference must not imply a split."""
        self.assertEqual(
            self.routers(
                {"DATABASE_URL": SHARED, "DATABASE_URL_XRPL": SHARED_NO_PORT}
            ),
            [],
        )
