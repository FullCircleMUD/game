"""
Worker-thread dispatch that releases its database connections.

Django holds connections in thread-local storage: one per (thread,
alias), opened lazily on first use. Nothing in a Twisted worker thread
ever closes them. The ``request_started``/``request_finished`` signals
that drive ``close_old_connections()`` fire only for the web request
cycle, so a thread dispatched with ``deferToThread`` opens its
connections and keeps them for the life of the thread — and the reactor
thread pool holds its threads indefinitely.

The result is a fixed pool of idle connections per process, one for each
alias each pooled thread has ever touched, multiplied by the number of
game processes. Measured against ``max_connections = 50``: 47 idle,
spread across four databases, with the shop commands and the web server
both refused.

The close has to happen on the worker thread. The call site, the
callback and the errback all run on the reactor thread, and
``close_all()`` there would walk the reactor thread's own connections
rather than the worker's. Wrapping the target function is the only place
the ``finally`` executes on the right side of the thread boundary.

``close_all()`` on a thread that opened nothing is a no-op, so this is
used for every worker dispatch rather than only the ones known to touch
the ORM. A function that does not query today is one edit away from
doing so, and the call site is not where that would be noticed.

Usage::

    from utils.db_threads import defer_to_db_thread

    d = defer_to_db_thread(blocking_fn, arg1, arg2)
    d.addCallback(lambda result: _on_success(caller, result))
    d.addErrback(lambda failure: _on_error(caller, failure))

Enforced by ``tests/test_defer_call_sites.py``, which fails the build on
a bare ``twisted.internet.threads`` import outside this module.
"""

from django.db import connections
from twisted.internet import threads


def defer_to_db_thread(fn, *args, **kwargs):
    """Run ``fn`` on a worker thread, closing its DB connections after.

    A drop-in replacement for ``threads.deferToThread`` — same argument
    forwarding, same Deferred, so callbacks and errbacks are unchanged.

    The connections are closed in a ``finally``, so the failure path
    releases them too. That is the path that matters: an exhausted pool
    makes every subsequent query raise, and a trailing close would leak
    a connection on each one.

    Args:
        fn (callable): the blocking work, run on a worker thread.
        *args: positional arguments for ``fn``.
        **kwargs: keyword arguments for ``fn``.

    Returns:
        Deferred: fires with ``fn``'s return value, or its failure.
    """

    def run():
        try:
            return fn(*args, **kwargs)
        finally:
            connections.close_all()

    return threads.deferToThread(run)
