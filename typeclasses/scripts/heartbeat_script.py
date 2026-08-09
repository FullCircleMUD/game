"""
HeartbeatMixin — tracks whether a global service script is actually
ticking and actually doing its work, not just whether its ScriptDB row
exists.

Two separate signals, both in-memory (ndb) and per-process:

    last_repeat — stamped every time at_repeat() fires at all, proving
        the LoopingCall itself hasn't detached. Set unconditionally,
        before any gate check or try/except — even a tick whose body
        immediately raises still proves the ticker is alive.

    last_work — stamped only when the script's actual periodic work
        executes, as the last line inside a try block, right before
        except — any exception skips it, so it never advances on a
        failed tick.

For most scripts every tick *is* the work (no internal gate), so
record_heartbeat() stamps both together. A few scripts tick far more
often than their real work fires (the hourly pipeline scripts,
durability_decay_service) — those call record_repeat() unconditionally
and record_work() only inside their own gate, so staleness on
last_work reflects the actual batch cadence rather than the fast
sub-sampling interval.

ndb, not db: resets to unset on a process restart rather than carrying
a stale pre-persisted value forward — correct here, since the question
is "is this process's own ticker actually working right now."
"""


class HeartbeatMixin:
    """Mixin for global service scripts — provides heartbeat recording."""

    def record_repeat(self):
        from django.utils import timezone

        self.ndb.last_repeat = timezone.now()

    def record_work(self):
        from django.utils import timezone

        self.ndb.last_work = timezone.now()

    def record_heartbeat(self):
        """For scripts where every tick is real work — stamps both at once."""
        from django.utils import timezone

        now = timezone.now()
        self.ndb.last_repeat = now
        self.ndb.last_work = now
