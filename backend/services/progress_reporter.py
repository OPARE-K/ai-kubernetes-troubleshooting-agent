from typing import Callable

import socketio
from loguru import logger

from core.config import settings
from services.investigation_store import InvestigationStore

ProgressCallback = Callable[..., None]

INVESTIGATION_STEPS = [
    "checking_pods",
    "reading_logs",
    "analyzing_events",
    "inspecting_deployments",
    "checking_networking",
    "ai_reasoning",
    "root_cause_found",
]


def create_progress_reporter(
    investigation_id: str | None,
    store: InvestigationStore | None = None,
) -> ProgressCallback:
    realtime = _RealtimePublisher(investigation_id) if investigation_id else None
    if realtime:
        realtime.connect()

    def report(
        step: str,
        status: str = "complete",
        *,
        message: str | None = None,
        details: dict | None = None,
    ) -> None:
        if realtime:
            realtime.publish(step, status)
        if store:
            store.update_progress(step, status, message=message, details=details)

    return report


class _RealtimePublisher:
    """Publish investigation progress to InsForge realtime."""

    def __init__(self, investigation_id: str) -> None:
        self.channel = f"investigation:{investigation_id}"
        self._client: socketio.Client | None = None

    def connect(self) -> None:
        if not settings.insforge_api_key or not settings.insforge_base_url:
            logger.debug("InsForge realtime disabled — progress publishing skipped")
            return

        try:
            self._client = socketio.Client(reconnection=False, logger=False, engineio_logger=False)
            self._client.connect(
                settings.insforge_base_url,
                auth={"apiKey": settings.insforge_api_key},
                transports=["websocket"],
                wait_timeout=5,
            )
            self._client.emit("realtime:subscribe", {"channel": self.channel})
        except Exception as exc:
            logger.warning(f"InsForge realtime connect failed: {exc}")
            self._client = None

    def publish(self, step: str, status: str = "complete") -> None:
        if not self._client:
            return

        try:
            self._client.emit(
                "realtime:publish",
                {
                    "channel": self.channel,
                    "event": "progress",
                    "payload": {"step": step, "status": status},
                },
            )
        except Exception as exc:
            logger.warning(f"Failed to publish progress step '{step}': {exc}")

    def disconnect(self) -> None:
        if self._client and self._client.connected:
            try:
                self._client.disconnect()
            except Exception:
                pass
