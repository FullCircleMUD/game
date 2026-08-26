"""The telemetry API. Import the services from here, not from the modules."""

from telemetry.services.read import TelemetryReadService
from telemetry.services.write import TelemetryWriteService

__all__ = ["TelemetryReadService", "TelemetryWriteService"]
