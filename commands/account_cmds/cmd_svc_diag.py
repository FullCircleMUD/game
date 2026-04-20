"""
Superuser diagnostic: dump pipeline script state and snapshot counts.

Read-only. Reports, for each of the three pipeline scripts:
  - GLOBAL_SCRIPTS lookup result and dbref
  - All ScriptDB rows matching the key (>1 reveals duplication)
  - Live ndb._task state: running flag, callcount (polls since boot)
  - db.last_run_hour — the hour bucket this script last fired for
  - Time until the next wall-clock slot fire
  - Script age since creation

Plus a snapshot summary: row counts, distinct hours, latest hour for
EconomySnapshot / ResourceSnapshot / SaturationSnapshot.

Use cases: confirm ticker is polling (callcount climbing), confirm last
fire matches the current hour, spot duplicate rows the dedupe sweep
missed.
"""

from datetime import datetime, timedelta, timezone

from evennia import Command, GLOBAL_SCRIPTS, ScriptDB
from twisted.internet import threads

from commands.account_cmds.cmd_services import (
    PIPELINE_SLOT_MINUTES,
    _format_interval,
)
from server.conf.at_server_startstop import _PIPELINE_SCRIPTS


def _fmt_delta_secs(secs):
    if secs is None:
        return "None"
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs}s ({secs // 60}m {secs % 60}s)"
    return f"{secs}s ({secs // 3600}h {(secs % 3600) // 60}m)"


def _fmt_dt(dt):
    if dt is None:
        return "None"
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _seconds_until_slot(now, slot_minute):
    """Seconds from `now` until the next HH:slot_minute wall-clock moment."""
    target = now.replace(minute=slot_minute, second=0, microsecond=0)
    if target <= now:
        target = target + timedelta(hours=1)
    return int((target - now).total_seconds()), target


def _introspect_script(key, now):
    """Build the text report for one pipeline script. Reactor-thread work only."""
    lines = [f"|c--- {key} ---|n"]

    # A. GLOBAL_SCRIPTS lookup
    script = getattr(GLOBAL_SCRIPTS, key, None)
    if script is None:
        lines.append("  GLOBAL_SCRIPTS lookup: |rNone (missing)|n")
    else:
        lines.append(f"  GLOBAL_SCRIPTS lookup: found, dbref={script.dbref}")

    # B. Raw ScriptDB rows (duplicate detection)
    rows = list(ScriptDB.objects.filter(db_key=key))
    dup_tag = " |rDUPLICATES|n" if len(rows) > 1 else ""
    lines.append(f"  ScriptDB rows with this key: {len(rows)}{dup_tag}")
    for row in rows:
        lines.append(
            f"    id={row.id} active={row.db_is_active} "
            f"interval={row.db_interval} persistent={row.db_persistent}  "
            f"created={_fmt_dt(row.db_date_created)}"
        )

    if script is None:
        return "\n".join(lines)

    # C. Live ticker state on ndb._task
    task = getattr(script.ndb, "_task", None)
    if task is None:
        lines.append("  ndb._task: |rNone (ticker detached)|n")
    else:
        running = getattr(task, "running", "?")
        callcount = getattr(task, "callcount", "?")
        interval = getattr(task, "interval", "?")
        lines.append(
            f"  ndb._task: running={running}  "
            f"callcount={callcount} polls  tick_interval={interval}s"
        )

    # D. Scheduling state (the new-design load-bearing fields)
    slot_minute = PIPELINE_SLOT_MINUTES.get(key)
    last_run = script.db.last_run_hour
    lines.append(f"  db.last_run_hour: {_fmt_dt(last_run)}")
    if slot_minute is not None:
        secs_to_slot, slot_dt = _seconds_until_slot(now, slot_minute)
        current_hour_bucket = now.replace(minute=0, second=0, microsecond=0)
        already_ran_this_hour = last_run == current_hour_bucket
        status = " |g(already ran this hour)|n" if already_ran_this_hour else ""
        lines.append(
            f"  slot: HH:{slot_minute:02d}  "
            f"next fire at {_fmt_dt(slot_dt)} "
            f"({_fmt_delta_secs(secs_to_slot)}){status}"
        )

    # E. Legacy pause state — only shown when non-None
    paused_time = script.db._paused_time
    paused_callcount = script.db._paused_callcount
    if paused_time is not None or paused_callcount is not None:
        lines.append(
            f"  |ydb._paused_time|n: {paused_time}  "
            f"|ydb._paused_callcount|n: {paused_callcount}"
        )

    # F. Age
    created = script.db_date_created
    if created:
        age_secs = int((now - created).total_seconds())
        lines.append(
            f"  script created: {_fmt_dt(created)}  "
            f"(age {_fmt_delta_secs(age_secs)})"
        )

    return "\n".join(lines)


def _snapshot_summary():
    """DB-touching work. Runs in worker thread."""
    from blockchain.xrpl.models import (
        EconomySnapshot,
        ResourceSnapshot,
        SaturationSnapshot,
    )

    lines = ["|c--- Snapshot tables ---|n"]

    def _model_summary(label, qs):
        total = qs.count()
        distinct_hours = qs.values("hour").distinct().count()
        latest_row = qs.order_by("-hour").first()
        latest_hour = latest_row.hour if latest_row else None
        lines.append(
            f"  {label}: rows={total}  distinct_hours={distinct_hours}  "
            f"latest_hour={_fmt_dt(latest_hour)}"
        )

    _model_summary("EconomySnapshot   ", EconomySnapshot.objects.all())
    _model_summary("ResourceSnapshot  ", ResourceSnapshot.objects.all())
    _model_summary("SaturationSnapshot", SaturationSnapshot.objects.all())

    return "\n".join(lines)


class CmdSvcDiag(Command):
    """
    Dump pipeline script state and snapshot counts.

    Usage:
        svc_diag

    Read-only diagnostic. For each of the three hourly pipeline scripts
    (telemetry, saturation, spawn) shows:
      - GLOBAL_SCRIPTS lookup result + ScriptDB row count (>1 = duplicates)
      - ndb._task running flag and callcount (polls since boot)
      - db.last_run_hour (which hour this script last fired for)
      - Wall-clock slot + seconds until the next fire
      - Script age

    Also prints row/hour counts for EconomySnapshot, ResourceSnapshot,
    and SaturationSnapshot so script state can be cross-checked against
    what's actually in the DB.
    """

    key = "svc_diag"
    locks = "cmd:id(1)"
    help_category = "Admin"

    def func(self):
        now = datetime.now(timezone.utc)
        header = [
            "|w=== Service Ticker Diagnostic ===|n",
            f"  current UTC: {_fmt_dt(now)}",
            "",
        ]

        # Ticker introspection on the reactor thread (ndb is reactor-only).
        script_sections = [
            _introspect_script(key, now) for key, _, _ in _PIPELINE_SCRIPTS
        ]

        synchronous_text = "\n".join(header + script_sections)

        # DB counts go to a worker thread.
        d = threads.deferToThread(_snapshot_summary)
        d.addCallback(
            lambda snapshot_text: self.msg(
                synchronous_text + "\n\n" + snapshot_text
            )
        )
        d.addErrback(
            lambda f: self.msg(
                synchronous_text
                + f"\n\n|rSnapshot summary failed: {f.getErrorMessage()}|n"
            )
        )
