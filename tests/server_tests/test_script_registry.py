"""
Tests for the global-script registry in at_server_startstop.

Covers the declaration list (_SCRIPTS), the role/tag selector, and the
start/stop engine.

at_server_startstop has no module-level imports — every Evennia import
is function-local — so these tests run under plain unittest without a
gamedir. The engine functions are exercised by injecting a fake
`evennia` module into sys.modules for the duration of the call.

evennia test --settings settings tests.server_tests.test_script_registry
"""

import sys
import types
from unittest import TestCase
from unittest.mock import MagicMock, patch

from server.conf import at_server_startstop as ass


def _fake_evennia(existing=None):
    """Build a stand-in `evennia` module.

    Args:
        existing: dict of {script_key: script_object} that
            `getattr(GLOBAL_SCRIPTS, key, None)` should resolve. Keys
            absent from the dict resolve to None, which is how Evennia's
            container reports "no such script".
    """
    existing = existing or {}
    fake = MagicMock()

    class _Container:
        def __getattr__(self, item):
            try:
                return existing[item]
            except KeyError:
                raise AttributeError(item)

    fake.GLOBAL_SCRIPTS = _Container()
    fake.create_script = MagicMock()
    fake.logger = MagicMock()
    return fake


def _script_row(task_running=True):
    """A stand-in for an existing ScriptDB row's typeclass instance."""
    row = MagicMock()
    row.ndb._task = MagicMock() if task_running is not None else None
    if task_running is None:
        row.ndb._task = None
    else:
        row.ndb._task.running = task_running
    return row


class TestRoleConstants(TestCase):
    """The role sets are tuples of known role names."""

    KNOWN = {"shard", "router", "monolith"}

    def test_single_element_sets_are_tuples_not_strings(self):
        """A missing trailing comma silently yields a string, whose `in`
        checks then match substrings. Guard against the regression."""
        for name in ("SHARDED_ONLY_SHARD", "SHARDED_ONLY_ROUTER"):
            value = getattr(ass, name)
            self.assertIsInstance(value, tuple, f"{name} must be a tuple")
            self.assertEqual(len(value), 1)

    def test_all_role_sets_contain_only_known_roles(self):
        for name in (
            "ALL_ROLES", "SHARDED_ONLY_ALL", "SHARDED_ONLY_SHARD",
            "SHARDED_ONLY_ROUTER", "GAME_ROLES", "ROUTER_ROLES",
        ):
            value = getattr(ass, name)
            self.assertIsInstance(value, tuple, f"{name} must be a tuple")
            self.assertTrue(
                set(value) <= self.KNOWN,
                f"{name} has unknown roles: {set(value) - self.KNOWN}",
            )

    def test_monolith_is_first_class_not_derived(self):
        """A sharded-only set must be expressible — i.e. monolith is a
        role you opt into, not one implied by shard+router."""
        self.assertNotIn("monolith", ass.SHARDED_ONLY_ALL)


class TestScriptDeclarations(TestCase):
    """Structural integrity of _SCRIPTS itself."""

    KNOWN = {"shard", "router", "monolith"}

    def test_every_entry_is_a_four_tuple(self):
        for entry in ass._SCRIPTS:
            self.assertEqual(
                len(entry), 4,
                f"{entry[0] if entry else entry}: expected "
                "(key, path, roles, tags)",
            )

    def test_roles_and_tags_are_tuples_of_known_values(self):
        for key, _path, roles, tags in ass._SCRIPTS:
            self.assertIsInstance(roles, tuple, f"{key}: roles must be a tuple")
            self.assertIsInstance(tags, tuple, f"{key}: tags must be a tuple")
            self.assertTrue(roles, f"{key}: must declare at least one role")
            self.assertTrue(
                set(roles) <= self.KNOWN,
                f"{key}: unknown roles {set(roles) - self.KNOWN}",
            )

    def test_keys_are_unique(self):
        keys = [e[0] for e in ass._SCRIPTS]
        self.assertEqual(len(keys), len(set(keys)), "duplicate script keys")


class TestSelectScripts(TestCase):
    """_select_scripts filters by role and tag, ANDed."""

    SAMPLE = [
        ("regen", "path.Regen", ("shard", "monolith"), ()),
        ("spawn", "path.Spawn", ("shard",), ("pipeline",)),
        ("routery", "path.Routery", ("router", "monolith"), ()),
    ]

    def _select(self, **kwargs):
        with patch.object(ass, "_SCRIPTS", self.SAMPLE):
            return [k for k, _p in ass._select_scripts(**kwargs)]

    def test_no_filters_returns_everything(self):
        self.assertEqual(self._select(), ["regen", "spawn", "routery"])

    def test_role_filter(self):
        self.assertEqual(self._select(role="shard"), ["regen", "spawn"])
        self.assertEqual(self._select(role="monolith"), ["regen", "routery"])
        self.assertEqual(self._select(role="router"), ["routery"])

    def test_tag_filter(self):
        self.assertEqual(self._select(tag="pipeline"), ["spawn"])

    def test_filters_are_anded(self):
        self.assertEqual(self._select(role="shard", tag="pipeline"), ["spawn"])
        # A role that owns no pipeline scripts selects nothing, rather
        # than starting scripts that don't belong on it.
        self.assertEqual(self._select(role="router", tag="pipeline"), [])

    def test_unknown_role_selects_nothing(self):
        self.assertEqual(self._select(role="nonesuch"), [])

    def test_returns_key_path_pairs(self):
        with patch.object(ass, "_SCRIPTS", self.SAMPLE):
            self.assertEqual(
                ass._select_scripts(role="router"), [("routery", "path.Routery")]
            )


class TestStartScripts(TestCase):
    """start_scripts creates missing scripts and re-attaches stalled ones."""

    SAMPLE = [("regen", "path.Regen", ("shard", "monolith"), ())]

    def test_creates_when_missing(self):
        fake = _fake_evennia(existing={})
        with patch.dict(sys.modules, {"evennia": fake}), \
                patch.object(ass, "_SCRIPTS", self.SAMPLE):
            ass.start_scripts(role="shard")
        fake.create_script.assert_called_once_with(
            "path.Regen", key="regen", obj=None
        )

    def test_reattaches_when_row_exists_but_task_not_running(self):
        row = _script_row(task_running=False)
        fake = _fake_evennia(existing={"regen": row})
        with patch.dict(sys.modules, {"evennia": fake}), \
                patch.object(ass, "_SCRIPTS", self.SAMPLE):
            ass.start_scripts(role="shard")
        row.start.assert_called_once()
        fake.create_script.assert_not_called()

    def test_leaves_a_running_script_alone(self):
        row = _script_row(task_running=True)
        fake = _fake_evennia(existing={"regen": row})
        with patch.dict(sys.modules, {"evennia": fake}), \
                patch.object(ass, "_SCRIPTS", self.SAMPLE):
            ass.start_scripts(role="shard")
        row.start.assert_not_called()
        fake.create_script.assert_not_called()

    def test_role_that_owns_nothing_starts_nothing(self):
        fake = _fake_evennia(existing={})
        with patch.dict(sys.modules, {"evennia": fake}), \
                patch.object(ass, "_SCRIPTS", self.SAMPLE):
            ass.start_scripts(role="router")
        fake.create_script.assert_not_called()


class TestSafeStopScripts(TestCase):
    """safe_stop_scripts detaches this process's ticker, tolerantly."""

    SAMPLE = [("regen", "path.Regen", ("shard", "monolith"), ())]

    def test_stops_a_running_script(self):
        row = _script_row()
        fake = _fake_evennia(existing={"regen": row})
        with patch.dict(sys.modules, {"evennia": fake}), \
                patch.object(ass, "_SCRIPTS", self.SAMPLE):
            ass.safe_stop_scripts(role="shard")
        row.stop.assert_called_once()

    def test_missing_row_is_skipped_not_raised(self):
        fake = _fake_evennia(existing={})
        with patch.dict(sys.modules, {"evennia": fake}), \
                patch.object(ass, "_SCRIPTS", self.SAMPLE):
            ass.safe_stop_scripts(role="shard")  # must not raise

    def test_stop_failure_is_swallowed(self):
        row = _script_row()
        row.stop.side_effect = RuntimeError("boom")
        fake = _fake_evennia(existing={"regen": row})
        with patch.dict(sys.modules, {"evennia": fake}), \
                patch.object(ass, "_SCRIPTS", self.SAMPLE):
            ass.safe_stop_scripts(role="shard")  # must not raise
        fake.logger.log_trace.assert_called_once()


class TestBootEntryPoint(TestCase):
    """_start_scripts_for_this_role uses the role accessor, not settings."""

    def test_starts_scripts_for_the_reported_role(self):
        shards = MagicMock()
        shards.get_role.return_value = "shard"
        with patch.dict(sys.modules, {"evennia_shards": shards}), \
                patch.object(ass, "start_scripts") as start:
            ass._start_scripts_for_this_role()
        start.assert_called_once_with(role="shard")

    def test_router_role_is_passed_through(self):
        shards = MagicMock()
        shards.get_role.return_value = "router"
        with patch.dict(sys.modules, {"evennia_shards": shards}), \
                patch.object(ass, "start_scripts") as start:
            ass._start_scripts_for_this_role()
        start.assert_called_once_with(role="router")


class TestSelectScriptEntries(TestCase):
    """The three-column view, used to stamp roles onto each script."""

    SAMPLE = [
        ("regen", "path.Regen", ("shard", "monolith"), ()),
        ("routery", "path.Routery", ("router",), ("pipeline",)),
    ]

    def test_returns_roles_alongside_key_and_path(self):
        with patch.object(ass, "_SCRIPTS", self.SAMPLE):
            self.assertEqual(
                ass._select_script_entries(role="router"),
                [("routery", "path.Routery", ("router",))],
            )

    def test_two_column_view_matches_the_three_column_one(self):
        # _select_scripts is a projection of the same filter, not a second
        # implementation — callers unpacking pairs must keep working.
        with patch.object(ass, "_SCRIPTS", self.SAMPLE):
            for role in (None, "shard", "router", "monolith"):
                self.assertEqual(
                    ass._select_scripts(role=role),
                    [(k, p) for k, p, _r in ass._select_script_entries(role=role)],
                )


class TestDeclareScriptRoles(TestCase):
    """Scripts are stamped with the roles allowed to run them.

    The _SCRIPTS table gates what a process *creates*. Evennia's boot walk
    attaches a LoopingCall to any active row still carrying a pause marker
    and knows nothing about roles, so without this stamp the first process
    to boot picks up every script in the cluster.
    """

    SAMPLE = [("regen", "path.Regen", ("shard", "monolith"), ())]

    def _shards(self, role):
        """A stand-in evennia_shards exposing only what the stamp reads."""
        mod = types.ModuleType("evennia_shards")
        mod.OWNING_ROLES_ATTR = "owning_roles"
        mod.ROLE_MONOLITH = "monolith"
        mod.get_role = lambda: role
        return mod

    def test_stamps_declared_roles_on_creation(self):
        created = MagicMock()
        fake = _fake_evennia(existing={})
        fake.create_script.return_value = created
        with patch.dict(sys.modules, {"evennia": fake,
                                      "evennia_shards": self._shards("shard")}), \
                patch.object(ass, "_SCRIPTS", self.SAMPLE):
            ass.start_scripts(role="shard")
        created.attributes.add.assert_called_once_with(
            "owning_roles", ["shard", "monolith"]
        )

    def test_stamps_before_reattaching(self):
        # start() goes through the shards guard, which reads the attribute
        # to decide whether the attach is allowed — so the stamp has to
        # land first or the re-attach is refused.
        row = _script_row(task_running=False)
        fake = _fake_evennia(existing={"regen": row})
        manager = MagicMock()
        manager.attach_mock(row.attributes.add, "stamp")
        manager.attach_mock(row.start, "start")
        with patch.dict(sys.modules, {"evennia": fake,
                                      "evennia_shards": self._shards("shard")}), \
                patch.object(ass, "_SCRIPTS", self.SAMPLE):
            ass.start_scripts(role="shard")
        self.assertEqual([c[0] for c in manager.mock_calls], ["stamp", "start"])

    def test_no_stamp_in_monolith(self):
        # Monolith is a single process that is the whole world — nothing to
        # keep a script away from.
        created = MagicMock()
        fake = _fake_evennia(existing={})
        fake.create_script.return_value = created
        with patch.dict(sys.modules, {"evennia": fake,
                                      "evennia_shards": self._shards("monolith")}), \
                patch.object(ass, "_SCRIPTS", self.SAMPLE):
            ass.start_scripts(role="monolith")
        created.attributes.add.assert_not_called()

    def test_no_stamp_without_shards_installed(self):
        created = MagicMock()
        fake = _fake_evennia(existing={})
        fake.create_script.return_value = created
        with patch.dict(sys.modules, {"evennia": fake, "evennia_shards": None}), \
                patch.object(ass, "_SCRIPTS", self.SAMPLE):
            ass.start_scripts(role="shard")
        created.attributes.add.assert_not_called()

    def test_a_running_script_is_left_entirely_alone(self):
        row = _script_row(task_running=True)
        fake = _fake_evennia(existing={"regen": row})
        with patch.dict(sys.modules, {"evennia": fake,
                                      "evennia_shards": self._shards("shard")}), \
                patch.object(ass, "_SCRIPTS", self.SAMPLE):
            ass.start_scripts(role="shard")
        row.attributes.add.assert_not_called()
        row.start.assert_not_called()
