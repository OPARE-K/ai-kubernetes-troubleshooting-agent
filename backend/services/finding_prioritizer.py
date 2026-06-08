"""Rank investigation findings: user workloads before system noise."""

from __future__ import annotations

from typing import Any

from loguru import logger

from ai.kubectl_commands import build_pod_failure_kubectl_commands
from services.diagnosis_format import compute_fallback_confidence

SYSTEM_NAMESPACES = {
    "kube-system",
    "kube-public",
    "kube-node-lease",
    "local-path-storage",
}

WORKLOAD_FAILURE_MARKERS = (
    "Failed",
    "Error",
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "OOMKilled",
    "Evicted",
    "CreateContainerConfigError",
    "CreateContainerError",
    "RunContainerError",
    "exited with code",
    "Pending with container errors",
    "Container not ready",
)


def is_system_namespace(namespace: str) -> bool:
    return namespace in SYSTEM_NAMESPACES


def finding_scope(namespace: str) -> str:
    return "system" if is_system_namespace(namespace) else "user_workload"


def _severity_score(entry: dict[str, Any]) -> int:
    namespace = entry.get("namespace", "")
    status = str(entry.get("status", ""))
    phase = str(entry.get("phase", ""))
    is_user = not is_system_namespace(namespace)

    if is_user:
        if phase == "Failed" or any(marker in status for marker in WORKLOAD_FAILURE_MARKERS):
            return 100
        if "High restart count" in status:
            return 70
        if "Pending" in status:
            return 65
        return 60

    if "High restart count" in status:
        return 20
    if phase == "Failed" or any(marker in status for marker in WORKLOAD_FAILURE_MARKERS):
        return 45
    return 30


def _annotate_pod_finding(entry: dict[str, Any]) -> dict[str, Any]:
    annotated = dict(entry)
    annotated["scope"] = finding_scope(entry.get("namespace", ""))
    annotated["priority_score"] = _severity_score(entry)
    return annotated


def _best_per_pod(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in findings:
        key = (entry.get("namespace", ""), entry.get("name", ""))
        current = best.get(key)
        if not current or entry["priority_score"] > current["priority_score"]:
            best[key] = entry
        elif (
            entry["priority_score"] == current["priority_score"]
            and entry.get("container")
            and not current.get("container")
        ):
            best[key] = entry
    return list(best.values())


def _sort_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        findings,
        key=lambda entry: (
            0 if entry.get("scope") == "user_workload" else 1,
            -entry.get("priority_score", 0),
            entry.get("namespace", ""),
            entry.get("name", ""),
        ),
    )


def _build_recommended_issue(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "pod",
        "namespace": entry.get("namespace"),
        "name": entry.get("name"),
        "container": entry.get("container", ""),
        "phase": entry.get("phase", ""),
        "reason": entry.get("status", ""),
        "exit_code": entry.get("exit_code"),
        "summary": (
            f"User workload pod {entry.get('namespace')}/{entry.get('name')} "
            f"is failing ({entry.get('status')})."
        ),
    }


def build_priority_analysis(investigation: dict[str, Any]) -> dict[str, Any]:
    pods = investigation.get("pods", {})
    raw_findings = pods.get("problematic_pods", [])
    annotated = [_annotate_pod_finding(entry) for entry in raw_findings]
    deduped = _best_per_pod(annotated)

    user_findings = [f for f in deduped if f["scope"] == "user_workload"]
    system_findings = [f for f in deduped if f["scope"] == "system"]

    user_findings = _sort_findings(user_findings)
    system_findings = _sort_findings(system_findings)

    recommended = user_findings[0] if user_findings else (system_findings[0] if system_findings else None)
    recommended_issue = _build_recommended_issue(recommended) if recommended else None

    if user_findings:
        instruction = (
            "A user application/workload failure was detected. "
            f"Treat {user_findings[0]['namespace']}/{user_findings[0]['name']} "
            "as the PRIMARY root cause. "
            "List kube-system and infrastructure issues only as secondary findings "
            "unless they clearly explain the user workload failure."
        )
    elif system_findings:
        instruction = (
            "No user workload failures detected. "
            "System/infrastructure findings may be the primary root cause."
        )
    else:
        instruction = "No problematic pods were detected."

    if user_findings:
        logger.info(
            "Priority analysis — primary user workload: {}/{} ({})",
            user_findings[0]["namespace"],
            user_findings[0]["name"],
            user_findings[0]["status"],
        )
    if system_findings:
        logger.info(
            "Priority analysis — secondary system finding(s): {}",
            ", ".join(f"{f['namespace']}/{f['name']}" for f in system_findings[:3]),
        )

    return {
        "primary_user_findings": user_findings,
        "secondary_system_findings": system_findings,
        "recommended_primary_issue": recommended_issue,
        "prioritization_instruction": instruction,
    }


def enrich_investigation_priorities(investigation: dict[str, Any]) -> dict[str, Any]:
    pods = investigation.get("pods", {})
    raw_findings = pods.get("problematic_pods", [])
    annotated = [_annotate_pod_finding(entry) for entry in raw_findings]
    pods["problematic_pods"] = _sort_findings(_best_per_pod(annotated))

    analysis = build_priority_analysis(investigation)
    investigation["priority_analysis"] = analysis
    return investigation


def build_deterministic_diagnosis(
    investigation: dict[str, Any],
) -> dict[str, str | int | list[str]] | None:
    """Build a workload-first diagnosis without the LLM when evidence is clear."""
    analysis = investigation.get("priority_analysis", {})
    primary = analysis.get("recommended_primary_issue")
    if not primary or primary.get("type") != "pod":
        return None

    user_findings = analysis.get("primary_user_findings", [])
    if not user_findings:
        return None

    issue = user_findings[0]
    pod_ref = f"{issue['namespace']}/{issue['name']}"
    reason = issue.get("status", "failed")
    exit_code = issue.get("exit_code")
    exit_note = f" (exit code {exit_code})" if exit_code not in (None, 0) else ""

    secondary = analysis.get("secondary_system_findings", [])
    secondary_note = ""
    if secondary:
        names = ", ".join(f"{f['namespace']}/{f['name']}" for f in secondary[:2])
        secondary_note = (
            f" Secondary infrastructure findings also exist ({names}) "
            "but are unlikely to be the primary cause of the user workload failure."
        )

    kubectl_commands = build_pod_failure_kubectl_commands(investigation) or [
        f"kubectl describe pod {issue['name']} -n {issue['namespace']}",
    ]

    return {
        "root_cause": f"User workload pod {pod_ref} failed: {reason}{exit_note}",
        "explanation": (
            f"The investigation prioritized application workloads over system components. "
            f"Pod {pod_ref} is in phase {issue.get('phase', 'Unknown')} with status {reason}."
            f"{secondary_note}"
        ),
        "fix": (
            f"Inspect the failing workload with "
            f"'kubectl describe pod {issue['name']} -n {issue['namespace']}' and "
            f"'kubectl logs {issue['name']} -n {issue['namespace']} --previous' "
            f"to identify the failure."
        ),
        "kubectl_command": "\n".join(kubectl_commands),
        "kubectl_commands": kubectl_commands,
        "prevention_recommendation": (
            "Validate container commands, environment variables, and image configuration "
            "before deploying test workloads."
        ),
        "confidence": compute_fallback_confidence(investigation, issue),
        "confidence_reasoning": (
            "High-priority user workload failure detected with clear pod status evidence."
        ),
    }


def mentions_primary_issue(root_cause: str, primary: dict[str, Any]) -> bool:
    text = root_cause.lower()
    name = str(primary.get("name", "")).lower()
    namespace = str(primary.get("namespace", "")).lower()
    return name in text or f"{namespace}/{name}" in text
