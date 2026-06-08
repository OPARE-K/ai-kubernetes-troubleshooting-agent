"""Normalize diagnosis payloads for API and UI consumption."""

from __future__ import annotations

from typing import Any

from ai.kubectl_commands import (
    build_pod_failure_kubectl_commands,
    format_kubectl_commands,
)


def _primary_issue(investigation: dict[str, Any] | None) -> dict[str, Any] | None:
    if not investigation:
        return None

    analysis = investigation.get("priority_analysis", {})
    user_findings = analysis.get("primary_user_findings", [])
    if user_findings:
        return user_findings[0]

    pods = investigation.get("pods", {}).get("problematic_pods", [])
    return pods[0] if pods else None


def compute_fallback_confidence(
    investigation: dict[str, Any] | None,
    issue: dict[str, Any] | None = None,
) -> int:
    """Derive a numeric confidence score from investigation evidence."""
    issue = issue or _primary_issue(investigation)
    if not issue:
        return 0

    confidence = 50
    phase = str(issue.get("phase", ""))
    status = str(issue.get("status", ""))
    terminated_reason = str(issue.get("terminated_reason", ""))
    exit_code = issue.get("exit_code")

    has_strong_evidence = (
        phase == "Failed"
        or terminated_reason == "Error"
        or "Error" in status
        or exit_code not in (None, 0)
    )
    if has_strong_evidence:
        confidence = 75

    if issue.get("priority_score", 0) >= 100:
        confidence = 88

    return max(0, min(100, int(confidence)))


def _normalize_commands(diagnosis: dict[str, Any]) -> list[str]:
    commands = diagnosis.get("kubectl_commands")
    if isinstance(commands, list):
        normalized = [str(command).strip() for command in commands if str(command).strip()]
        if normalized:
            return normalized

    single = str(
        diagnosis.get("kubectl_command")
        or diagnosis.get("command")
        or ""
    ).strip()
    if not single:
        return []

    if "\n" in single:
        return [line.strip() for line in single.split("\n") if line.strip()]

    if single.count("kubectl ") > 1:
        parts = [
            part.strip()
            for part in single.split("kubectl ")
            if part.strip()
        ]
        return [f"kubectl {part}" if not part.startswith("kubectl") else part for part in parts]

    return [single]


def finalize_diagnosis(
    diagnosis: dict[str, Any],
    investigation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ensure diagnosis fields are complete and UI-friendly."""
    finalized = dict(diagnosis)

    commands = _normalize_commands(finalized)
    if not commands and investigation:
        commands = build_pod_failure_kubectl_commands(investigation)

    finalized["kubectl_commands"] = commands
    finalized["kubectl_command"] = (
        format_kubectl_commands(commands) if commands else str(finalized.get("kubectl_command", ""))
    )

    confidence = finalized.get("confidence")
    try:
        numeric_confidence = int(confidence)
    except (TypeError, ValueError):
        numeric_confidence = compute_fallback_confidence(investigation)

    finalized["confidence"] = max(0, min(100, numeric_confidence))

    if not str(finalized.get("confidence_reasoning", "")).strip():
        finalized["confidence_reasoning"] = (
            "Confidence derived from available Kubernetes investigation evidence."
        )

    return finalized


def build_ai_unavailable_diagnosis(
    investigation: dict[str, Any] | None,
    reason: str,
    *,
    build_deterministic_diagnosis,
    generic_fallback_diagnosis,
) -> dict[str, Any]:
    """Prefer evidence-based deterministic diagnosis when AI is unavailable."""
    if investigation:
        deterministic = build_deterministic_diagnosis(investigation)
        if deterministic:
            return finalize_diagnosis(deterministic, investigation)

    return finalize_diagnosis(generic_fallback_diagnosis(reason), investigation)
