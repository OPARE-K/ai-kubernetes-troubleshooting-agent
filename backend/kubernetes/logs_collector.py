import re
from typing import Any

from kubernetes.executor import KubectlExecutor

MAX_LOG_LINES = 50
HIGHLIGHT_PATTERNS = [
    r"exception",
    r"error",
    r"failed",
    r"connection refused",
    r"connection timed out",
    r"no such file",
    r"missing.*env",
    r"imagepullbackoff",
    r"crash",
    r"fatal",
    r"panic",
    r"startup",
    r"denied",
]


class LogsCollector:
    """Collect concise logs from failed pods."""

    def __init__(self, executor: KubectlExecutor) -> None:
        self.executor = executor
        self._highlight_regex = re.compile("|".join(HIGHLIGHT_PATTERNS), re.IGNORECASE)

    def collect(self, problematic_pods: list[dict[str, str]]) -> dict[str, Any]:
        if not problematic_pods:
            return {
                "collected": [],
                "message": "No problematic pods found — no logs collected",
            }

        collected: list[dict[str, Any]] = []

        for pod in problematic_pods:
            name = pod["name"]
            namespace = pod["namespace"]
            log_entry = self._fetch_pod_logs(name, namespace, pod.get("status", ""))
            if log_entry:
                collected.append(log_entry)

        return {
            "collected": collected,
            "pods_checked": len(problematic_pods),
        }

    def _fetch_pod_logs(
        self, name: str, namespace: str, status: str
    ) -> dict[str, Any] | None:
        attempts = [[]]
        retry_statuses = (
            "CrashLoopBackOff",
            "Error",
            "OOMKilled",
            "CreateContainerConfigError",
            "ImagePullBackOff",
            "ErrImagePull",
            "RunContainerError",
            "High restart",
        )
        if any(marker in status for marker in retry_statuses):
            attempts.append(["--previous"])

        for extra_args in attempts:
            args = [
                "logs",
                name,
                "-n",
                namespace,
                "--tail",
                str(MAX_LOG_LINES),
                *extra_args,
            ]
            result = self.executor.run(*args, timeout=30)

            if result.success and result.stdout.strip():
                return self._build_log_entry(
                    name, namespace, result.stdout, used_previous="--previous" in extra_args
                )

        return {
            "pod": name,
            "namespace": namespace,
            "highlights": [],
            "recent_lines": [],
            "message": "No logs available for this pod",
        }

    def _build_log_entry(
        self, name: str, namespace: str, raw_logs: str, used_previous: bool
    ) -> dict[str, Any]:
        lines = raw_logs.strip().splitlines()
        recent_lines = lines[-MAX_LOG_LINES:]
        highlights = [
            line.strip()
            for line in recent_lines
            if self._highlight_regex.search(line)
        ]

        return {
            "pod": name,
            "namespace": namespace,
            "highlights": highlights[:15],
            "recent_lines": recent_lines[-20:],
            "line_count": len(recent_lines),
            "source": "previous_container" if used_previous else "current_container",
        }
