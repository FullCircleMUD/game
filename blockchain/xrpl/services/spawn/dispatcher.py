"""
Dispatcher — routes planned placements to whoever owns their targets.

The planner decides placements without caring where they will be carried
out. This module gets them to the right process:

- **monolith** — hands the whole list straight to the executor. This is not
  an optimisation, it is required: ``send_message()`` raises
  ``MessageBusError`` when ``to_shard == from_shard``, and in monolith
  there is only one process.
- **sharded** — buckets by owning shard and sends one bus message per shard,
  which that shard's message handler passes to its own executor.

Each placement already carries the ``shard_id`` it was discovered with, so
routing needs no further database work — target ownership came back from the
same query that found the targets in the first place.

``shard_id`` is stripped when the payload is built. It is routing
information, and the message's ``to_shard`` already carries it; a shard
receiving a message does not need each entry to repeat which shard it is.
The wire format stays the four fields the executor requires.
"""

from blockchain.xrpl.services.spawn.log import spawn_log

MESSAGE_KIND = "spawn_placements"


def dispatch(placements):
    """Send placements to the processes that own their targets.

    Args:
        placements: list of placement dicts from the planner, each carrying
            ``shard_id`` (None in monolith).

    Returns:
        int — units placed locally. Zero in sharded mode, where placement
        happens on the receiving shards and nothing is reported back.
    """
    from evennia_shards import ROLE_MONOLITH, get_role

    if not placements:
        return 0

    if get_role() == ROLE_MONOLITH:
        from blockchain.xrpl.services.spawn.executor import execute

        return execute(_strip_routing(placements))

    _dispatch_to_shards(placements)
    return 0


def group_by_shard(placements):
    """Bucket placements by the shard that owns each target.

    Placements with no shard are dropped: a target the planner could not
    attribute to a shard cannot be routed, and spawning onto anything not
    shard-owned is not permitted.
    """
    grouped = {}
    unrouted = 0
    for placement in placements:
        shard_id = placement.get("shard_id")
        if not shard_id:
            unrouted += 1
            continue
        grouped.setdefault(shard_id, []).append(placement)

    if unrouted:
        spawn_log(
            f"dispatch: dropped {unrouted} placement(s) with no owning shard",
            level="WARN",
        )
    return grouped


def _strip_routing(placements):
    """Remove routing fields, leaving what the executor consumes."""
    return [
        {key: value for key, value in placement.items() if key != "shard_id"}
        for placement in placements
    ]


def _dispatch_to_shards(placements):
    """One bus message per shard holding that shard's placements."""
    from evennia_shards import send_message

    for shard_id, group in group_by_shard(placements).items():
        payload = {"placements": _strip_routing(group)}
        try:
            send_message(MESSAGE_KIND, payload, to_shard=shard_id)
            spawn_log(
                f"dispatch: sent {len(group)} placement(s) to {shard_id}"
            )
        except Exception as err:
            # A shard that cannot be reached simply misses this tick. The
            # router does not retry or re-bank — the next cycle re-measures
            # the world and any shortfall returns as budget.
            spawn_log(
                f"dispatch: failed sending {len(group)} placement(s) to "
                f"{shard_id}: {type(err).__name__}: {err}",
                level="ERROR",
            )
