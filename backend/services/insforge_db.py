from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from core.config import settings

PROGRESS_STEPS = [
    "pods",
    "logs",
    "events",
    "deployments",
    "networking",
    "ai_diagnosis",
]

STEP_MESSAGES = {
    "pods": "Checking pod health across the cluster",
    "logs": "Collecting logs from problematic pods",
    "events": "Analyzing Kubernetes events",
    "deployments": "Inspecting deployment health",
    "networking": "Checking services and networking",
    "ai_diagnosis": "Running AI root cause analysis",
}

INTERNAL_TO_DB_STEP = {
    "checking_pods": "pods",
    "reading_logs": "logs",
    "analyzing_events": "events",
    "inspecting_deployments": "deployments",
    "checking_networking": "networking",
    "ai_reasoning": "ai_diagnosis",
    "root_cause_found": "ai_diagnosis",
}


class InsforgeDatabase:
    """Minimal InsForge REST client for backend persistence."""

    def __init__(self) -> None:
        self.base_url = settings.insforge_base_url.rstrip("/")
        self.api_key = settings.insforge_api_key

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _headers(self, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _request(
        self,
        method: str,
        table: str,
        *,
        json_body: Any = None,
        params: dict[str, str] | None = None,
        prefer: str | None = None,
    ) -> bool:
        if not self.enabled:
            logger.debug("InsForge database persistence disabled")
            return False

        url = f"{self.base_url}/api/database/records/{table}"
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.request(
                    method,
                    url,
                    headers=self._headers(prefer),
                    json=json_body,
                    params=params,
                )
            if response.status_code >= 400:
                logger.warning(
                    f"InsForge {method} {table} failed ({response.status_code}): "
                    f"{response.text[:300]}"
                )
                return False
            return True
        except Exception as exc:
            logger.warning(f"InsForge {method} {table} error: {exc}")
            return False

    def insert(self, table: str, rows: list[dict[str, Any]], *, prefer: str | None = None) -> bool:
        return self._request("POST", table, json_body=rows, prefer=prefer)

    def patch(
        self,
        table: str,
        filters: dict[str, str],
        payload: dict[str, Any],
        *,
        prefer: str | None = None,
    ) -> bool:
        params = {key: f"eq.{value}" for key, value in filters.items()}
        return self._request("PATCH", table, json_body=payload, params=params, prefer=prefer)

    def insert_progress(
        self,
        investigation_id: str,
        step: str,
        status: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> bool:
        row = {
            "investigation_id": investigation_id,
            "step": step,
            "status": status,
            "message": message or STEP_MESSAGES.get(step, step),
            "details": details,
        }
        return self.insert("investigation_progress", [row], prefer="return=representation")

    def update_progress(
        self,
        investigation_id: str,
        step: str,
        status: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        payload: dict[str, Any] = {
            "status": status,
            "message": message or STEP_MESSAGES.get(step, step),
            "updated_at": now,
        }
        if details is not None:
            payload["details"] = details
        return self.patch(
            "investigation_progress",
            {"investigation_id": investigation_id, "step": step},
            payload,
        )
