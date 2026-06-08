from datetime import datetime, timezone
from typing import Any

from loguru import logger

from services.insforge_db import (
    INTERNAL_TO_DB_STEP,
    PROGRESS_STEPS,
    STEP_MESSAGES,
    InsforgeDatabase,
)


def extract_namespace(investigation: dict[str, Any]) -> str:
    pods = investigation.get("pods", {}).get("problematic_pods", [])
    if pods:
        return pods[0].get("namespace", "default")
    return "cluster"


class InvestigationStore:
    """Persist investigation lifecycle and per-step progress to InsForge."""

    def __init__(self, investigation_id: str | None, user_id: str | None) -> None:
        self.investigation_id = investigation_id
        self.user_id = user_id
        self.db = InsforgeDatabase()
        self.active = bool(
            investigation_id and user_id and self.db.enabled
        )

    def start_investigation(self) -> None:
        if not self.active or not self.investigation_id or not self.user_id:
            return

        created = self.db.insert(
            "investigations",
            [
                {
                    "id": self.investigation_id,
                    "user_id": self.user_id,
                    "status": "running",
                }
            ],
            prefer="return=representation",
        )
        if not created:
            logger.warning("Failed to create investigations row")
            return

        for step in PROGRESS_STEPS:
            self.db.insert_progress(
                self.investigation_id,
                step,
                "pending",
                message=f"Waiting to start: {STEP_MESSAGES[step]}",
            )

        logger.info(f"Created investigations record {self.investigation_id}")

    def update_progress(
        self,
        internal_step: str,
        status: str,
        *,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if not self.active or not self.investigation_id:
            return

        db_step = INTERNAL_TO_DB_STEP.get(internal_step)
        if not db_step:
            return

        db_status = status
        if status == "complete":
            db_status = "completed"

        self.db.update_progress(
            self.investigation_id,
            db_step,
            db_status,
            message=message or STEP_MESSAGES.get(db_step),
            details=details,
        )

    def complete_investigation(
        self,
        investigation_data: dict[str, Any],
        diagnosis_data: dict[str, Any],
    ) -> None:
        if not self.active or not self.investigation_id:
            return

        now = datetime.now(timezone.utc).isoformat()
        self.db.patch(
            "investigations",
            {"id": self.investigation_id},
            {
                "status": "completed",
                "root_cause": diagnosis_data.get("root_cause"),
                "namespace": extract_namespace(investigation_data),
                "confidence": diagnosis_data.get("confidence", 0),
                "diagnosis": diagnosis_data,
                "investigation": investigation_data,
                "completed_at": now,
            },
        )
        self.update_progress(
            "root_cause_found",
            "completed",
            message="Investigation completed",
            details={"confidence": diagnosis_data.get("confidence", 0)},
        )
        logger.info(f"Completed investigations record {self.investigation_id}")

    def fail_investigation(self, message: str) -> None:
        if not self.active or not self.investigation_id:
            return

        now = datetime.now(timezone.utc).isoformat()
        self.db.patch(
            "investigations",
            {"id": self.investigation_id},
            {
                "status": "failed",
                "root_cause": "Investigation failed",
                "completed_at": now,
            },
        )
        self.db.update_progress(
            self.investigation_id,
            "pods",
            "failed",
            message=message,
        )
        logger.warning(f"Marked investigations record {self.investigation_id} as failed")
