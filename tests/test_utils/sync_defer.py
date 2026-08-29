"""
Test utility — synchronous replacement for utils.db_threads.defer_to_db_thread.

In tests there is no running Twisted reactor, so the real helper would never
deliver results. This helper creates an already-fired Deferred so callbacks
execute inline (synchronously).

Usage in tests:
    from tests.test_utils.sync_defer import patch_defer_to_db_thread

    @patch_defer_to_db_thread("commands.npc_cmds.cmdset_resource_shop")
    def test_something(self):
        ...
"""

from functools import wraps
from unittest.mock import patch

from twisted.internet.defer import succeed, fail
from twisted.python.failure import Failure


def _sync_defer_to_thread(fn, *args, **kwargs):
    """Run fn synchronously, return an already-fired Deferred."""
    try:
        result = fn(*args, **kwargs)
        return succeed(result)
    except Exception as e:
        return fail(Failure(e))


def patch_defer_to_db_thread(module_path):
    """
    Decorator that patches defer_to_db_thread in the given module.

    Args:
        module_path: dotted module path importing defer_to_db_thread.
                     e.g. "commands.npc_cmds.cmdset_resource_shop"
    """
    return patch(f"{module_path}.defer_to_db_thread",
                 side_effect=_sync_defer_to_thread)
