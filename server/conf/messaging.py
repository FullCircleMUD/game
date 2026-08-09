"""
Cross-shard message handling for FCM.

The `evennia-shards` message bus is a Postgres table polled twice a second
by each process. The library ships the transport and a base handler covering
its own message kinds; a consumer game adds its own kinds by subclassing
`MessageHandler` and passing an instance to `start_message_bus()`.

Placed beside `at_server_startstop.py` because that is what starts the
polling loop — the handler and the call that installs it belong together.

`super().handle(message)` runs first in every override, so the library's own
kinds keep working: `ping` / `ping_received`, `undeliverable_reply`, and the
delivery primitives `obj_msg` / `account_msg` / `room_msg` /
`flush_from_cache` that cross-shard movement depends on.
"""

from evennia_shards import MessageHandler

from blockchain.xrpl.services.nft_token_patch import MESSAGE_KIND as NFT_PATCH_KIND
from blockchain.xrpl.services.spawn.dispatcher import MESSAGE_KIND as SPAWN_KIND
from blockchain.xrpl.services.spawn.log import spawn_log
from blockchain.xrpl.services.spawn.quest_debt import QUEST_DEBT_KIND
from utils.broadcast import MESSAGE_KIND as BROADCAST_KIND


class FCMMessageHandler(MessageHandler):
    """Routes FCM's own message kinds, deferring to the library first."""

    def handle(self, message) -> bool:
        if super().handle(message):
            return True

        if message.kind == SPAWN_KIND:
            return self._handle_spawn_placements(message)

        if message.kind == QUEST_DEBT_KIND:
            return self._handle_quest_debt(message)

        if message.kind == NFT_PATCH_KIND:
            return self._handle_nft_token_patch_sweep(message)

        if message.kind == BROADCAST_KIND:
            return self._handle_broadcast(message)

        return False

    def _handle_quest_debt(self, message) -> bool:
        """Apply debt a shard reported for a reward it has already given.

        Always returns True. The reward is spent either way, so retrying
        could only double-count the debt — and unlike placements there is no
        clamp to bound that.
        """
        from blockchain.xrpl.services.spawn.quest_debt import apply_quest_debt

        apply_quest_debt(message.payload)
        return True

    def _handle_spawn_placements(self, message) -> bool:
        """Carry out placements the router decided for this shard.

        Always returns True, even when individual placements fail.

        The return value tells the bus whether to *retry*, not whether the
        work succeeded — a falsy return leaves the row in place to be
        processed again on the next poll. Re-running placements is not safe:
        the executor's headroom clamp makes a duplicate mostly harmless, but
        if a player loots the target in between, the room reopens and the
        retry places a second copy. Failures are logged and dropped, which
        matches the router's own fire-and-forget dispatch — the next hourly
        cycle re-measures the world and any shortfall returns as budget.
        """
        from blockchain.xrpl.services.spawn.executor import execute

        placements = (message.payload or {}).get("placements") or []
        placed = execute(placements)
        spawn_log(
            f"received: {len(placements)} placement(s) from "
            f"{message.from_shard} -> {placed} unit(s) placed"
        )
        return True

    def _handle_nft_token_patch_sweep(self, message) -> bool:
        """Reconcile this shard's own NFT items against the mirror.

        The router already updated NFTGameState before dispatching this
        trigger — the payload carries no data, this shard just checks
        its own resident objects against the now-current mirror.

        Always returns True. Re-running the sweep is harmless: an object
        already holding a real token_id is skipped, so a duplicate
        message finds nothing left to do.
        """
        from blockchain.xrpl.services.nft_token_patch import apply_local_patches

        apply_local_patches()
        return True

    def _handle_broadcast(self, message) -> bool:
        """Announce a router-dispatched message to this shard's sessions."""
        from utils.broadcast import broadcast_to_local_sessions

        payload = message.payload or {}
        broadcast_to_local_sessions(
            payload.get("caller_name", "Admin"), payload.get("message", ""),
        )
        return True
