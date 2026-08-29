"""
Tests for worker-thread dispatch and the call-site rule it depends on.

Two halves. The first is the helper's own contract: it forwards to the
wrapped function, returns a Deferred carrying the result, and closes the
thread's database connections whether the work succeeded or raised.

The second is the guard. The helper only helps at call sites that use
it, so a bare ``threads.deferToThread`` reintroduces the leak silently —
the code looks right, the connection is never released, and nothing
fails until the pool is exhausted. The guard makes that a build failure
instead of a discovery, which is the only reason the convention holds.

evennia test --settings settings tests.utils_tests.test_db_threads
"""

import pathlib
import re
from unittest import TestCase
from unittest.mock import patch

from twisted.internet.defer import Deferred

from tests.test_utils.sync_defer import _sync_defer_to_thread
from utils.db_threads import defer_to_db_thread


# No reactor runs under test, so the real dispatch would never deliver.
# Patched one level below the helper, leaving its wrapper — the part
# under test — intact.
_sync_dispatch = patch(
    "utils.db_threads.threads.deferToThread", _sync_defer_to_thread
)


GAME_DIR = pathlib.Path(__file__).resolve().parents[2]

# The helper is the one module allowed to import Twisted's threads API;
# this file is exempt because naming the banned spelling in a failure
# message is how the guard explains itself.
EXEMPT = {GAME_DIR / "utils" / "db_threads.py", pathlib.Path(__file__).resolve()}

# `from twisted.internet import threads`, with or without other names
# alongside it, which is how the function-local imports are spelled.
TWISTED_THREADS_IMPORT = re.compile(
    r"^\s*from twisted\.internet import .*\bthreads\b", re.M
)

BARE_DEFER = re.compile(r"(?<![\w.])threads\.deferToThread\s*\(")


def _game_sources():
    """Every .py file in the game dir except the exempt ones and caches."""
    for path in GAME_DIR.rglob("*.py"):
        if "__pycache__" in path.parts or path.resolve() in EXEMPT:
            continue
        yield path


@_sync_dispatch
class TestDeferToDbThread(TestCase):
    """The helper's own contract."""

    def test_forwards_args_and_returns_result(self):
        d = defer_to_db_thread(lambda a, b: a + b, 2, b=3)

        self.assertIsInstance(d, Deferred)
        seen = []
        d.addCallback(seen.append)
        self.assertEqual(seen, [5])

    @patch("utils.db_threads.connections")
    def test_closes_connections_on_success(self, mock_connections):
        defer_to_db_thread(lambda: "ok")

        mock_connections.close_all.assert_called_once()

    @patch("utils.db_threads.connections")
    def test_closes_connections_when_work_raises(self, mock_connections):
        """The failure path is the one that matters — an exhausted pool
        makes every query raise, so a leak here compounds itself."""

        def boom():
            raise RuntimeError("no")

        d = defer_to_db_thread(boom)
        d.addErrback(lambda failure: failure.trap(RuntimeError))

        mock_connections.close_all.assert_called_once()


class TestNoBareDeferToThread(TestCase):
    """The guard — see the module docstring."""

    def test_no_module_imports_twisted_threads(self):
        offenders = [
            str(path.relative_to(GAME_DIR))
            for path in _game_sources()
            if TWISTED_THREADS_IMPORT.search(path.read_text())
        ]

        self.assertEqual(
            offenders,
            [],
            "These modules import twisted.internet.threads directly. Use "
            "`from utils.db_threads import defer_to_db_thread` instead — a "
            "bare deferToThread never closes its database connections:\n  "
            + "\n  ".join(offenders),
        )

    def test_no_module_calls_defer_to_thread(self):
        offenders = [
            str(path.relative_to(GAME_DIR))
            for path in _game_sources()
            if BARE_DEFER.search(path.read_text())
        ]

        self.assertEqual(
            offenders,
            [],
            "These modules call threads.deferToThread(). Use "
            "defer_to_db_thread() so the worker thread releases its "
            "database connections:\n  " + "\n  ".join(offenders),
        )
