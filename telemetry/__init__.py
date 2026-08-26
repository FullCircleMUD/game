"""Telemetry — play sessions and the hourly economy/saturation snapshots.

Nothing outside this package touches the snapshot tables. Producers call
``TelemetryWriteService``; consumers call ``TelemetryReadService``.
"""
