"""
Test utility — synchronous replacement for twisted.internet.threads.deferToThread.

In tests there is no running Twisted reactor, so deferToThread would never
deliver results. This helper creates an already-fired Deferred so callbacks
execute inline (synchronously).

Usage in tests:
    from tests.test_utils.sync_defer import patch_deferToThread

    @patch_deferToThread("commands.npc_cmds.cmdset_resource_shop")
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


def patch_deferToThread(module_path):
    """
    Decorator that patches threads.deferToThread in the given module.

    Args:
        module_path: dotted module path where 'threads' is imported.
                     e.g. "commands.npc_cmds.cmdset_resource_shop"
    """
    return patch(f"{module_path}.threads.deferToThread",
                 side_effect=_sync_defer_to_thread)
