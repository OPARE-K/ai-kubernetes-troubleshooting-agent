from collections import Counter
from typing import Any

from kubernetes.executor import KubectlExecutor

INTERESTING_EVENT_REASONS = {
    "FailedScheduling",
    "BackOff",
    "FailedMount",
    "FailedPull",
    "ErrImagePull",
    "ImagePullBackOff",
    "Unhealthy",
    "Failed",
    "FailedCreate",
    "FailedKillPod",
    "Evicted",
    "OOMKilling",
    "Killing",
}


class EventsAnalyzer:
    """Analyze Kubernetes cluster events for troubleshooting signals."""

    def __init__(self, executor: KubectlExecutor) -> None:
        self.executor = executor

    def analyze(self) -> dict[str, Any]:
        result = self.executor.run(
            "get", "events", "--all-namespaces", "--sort-by=.lastTimestamp", "-o", "json"
        )

        if not result.success:
            return {
                "healthy": False,
                "error": result.stderr or "Failed to fetch events",
                "findings": [],
                "summary": {},
            }

        data = result.json_output()
        if not isinstance(data, dict):
            return {
                "healthy": False,
                "error": "Unexpected kubectl response format",
                "findings": [],
                "summary": {},
            }

        findings: list[dict[str, str]] = []
        reason_counter: Counter[str] = Counter()

        for event in data.get("items", []):
            reason = event.get("reason", "")
            if reason not in INTERESTING_EVENT_REASONS:
                continue

            involved = event.get("involvedObject", {})
            finding = {
                "type": event.get("type", "Unknown"),
                "reason": reason,
                "namespace": event.get("metadata", {}).get("namespace", "default"),
                "object": f"{involved.get('kind', 'Unknown')}/{involved.get('name', 'unknown')}",
                "message": event.get("message", ""),
                "count": str(event.get("count", 1)),
            }
            findings.append(finding)
            reason_counter[reason] += 1

        recent_findings = findings[-30:]

        return {
            "healthy": len(recent_findings) == 0,
            "total_events_scanned": len(data.get("items", [])),
            "findings": recent_findings,
            "summary": dict(reason_counter),
        }
