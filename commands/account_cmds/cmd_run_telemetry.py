"""
Superuser command: trigger a telemetry snapshot out of cycle.

The telemetry snapshot normally runs once per hour. This command forces
an immediate snapshot so economy data (AMM prices, circulation, velocity)
is available for the spawn system and economy dashboard.
"""

from evennia import Command


class CmdRunTelemetry(Command):
    """
    Force a telemetry snapshot now.

    Usage:
        run_telemetry

    Triggers the hourly economy + resource snapshot immediately.
    Updates AMM prices, circulation data, and velocity metrics
    used by the spawn system and the /markets/ web dashboard.
    """

    key = "run_telemetry"
    locks = "cmd:id(1)"
    help_category = "Economy"

    def func(self):
        from blockchain.xrpl.services.telemetry import TelemetryService

        self.msg("|yTaking telemetry snapshot...|n")
        TelemetryService.take_snapshot()
        self.msg("|gTelemetry snapshot complete.|n")
