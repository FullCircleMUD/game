"""CosignerKeepAliveScript — pings Render cosigner while players are online.

The cosigner runs on Render's free tier and spins down after ~15 min idle.
This script ticks every 10 minutes and, if any session is connected, fires
a /health ping to keep the service warm. See blockchain/xrpl/cosigner_ping.py.
"""

from evennia import DefaultScript
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import logger

from typeclasses.scripts.heartbeat_script import HeartbeatMixin


TICK_INTERVAL_SECONDS = 600  # 10 min — 5-min margin under Render's 15-min spindown


class CosignerKeepAliveScript(HeartbeatMixin, DefaultScript):
    """Global persistent script that pings the cosigner while any session is connected."""

    def at_script_creation(self):
        self.key = "cosigner_keepalive_service"
        self.desc = "Keeps Render cosigner warm while any session is connected"
        self.interval = TICK_INTERVAL_SECONDS
        self.persistent = True
        self.start_delay = True
        self.repeats = 0  # repeat forever

    def at_repeat(self):
        try:
            if not SESSIONS.get_sessions():
                self.record_heartbeat()
                return

            from blockchain.xrpl.cosigner_ping import warm_cosigner
            warm_cosigner()

            self.record_heartbeat()
        except Exception:
            logger.log_trace("cosigner_keepalive_service: tick failed")
