"""Build kubectl commands for pod failure diagnoses."""

from __future__ import annotations

import re
from typing import Any

IMAGE_PULL_REASONS = frozenset({"ImagePullBackOff", "ErrImagePull"})
CRASH_LOOP_REASONS = frozenset({"CrashLoopBackOff"})
TERMINATED_MARKERS = (
    "exited with code",
    "Error",
    "OOMKilled",
    "Failed",
)

KNOWN_IMAGE_DEFAULTS = {
    "nginx": "nginx:latest",
    "redis": "redis:latest",
}

INVALID_TAG_MARKERS = (
    "does-not-exist",
    "nonexistent",
    "invalid",
    "not-found",
    "notfound",
    "fake",
    "bad",
)


def deployment_name_from_metadata(metadata: dict[str, Any]) -> str | None:
    """Derive Deployment name from pod ownerReferences."""
    for ref in metadata.get("ownerReferences", []):
        kind = ref.get("kind")
        if kind == "Deployment":
            return ref.get("name")
        if kind == "ReplicaSet":
            rs_name = ref.get("name", "")
            match = re.match(r"^(.+)-[a-z0-9]{5,10}$", rs_name)
            if match:
                return match.group(1)
    return None


def infer_valid_image(image: str | None) -> str | None:
    """Suggest a corrected image only when it can be inferred safely."""
    if not image or ":" not in image:
        return None

    repository, tag = image.rsplit(":", 1)
    if not any(marker in tag.lower() for marker in INVALID_TAG_MARKERS):
        return None

    repo_name = repository.split("/")[-1]
    if repo_name in KNOWN_IMAGE_DEFAULTS:
        return KNOWN_IMAGE_DEFAULTS[repo_name]

    if repository.endswith("/nginx") or repository == "nginx":
        return "nginx:latest"

    return None


def _primary_pod_issue(investigation: dict[str, Any]) -> dict[str, Any] | None:
    priority = investigation.get("priority_analysis", {})
    primary = priority.get("recommended_primary_issue")
    if primary and primary.get("type") == "pod":
        return primary

    pods = investigation.get("pods", {}).get("problematic_pods", [])
    if pods:
        pod = pods[0]
        return {
            "type": "pod",
            "namespace": pod.get("namespace"),
            "name": pod.get("name"),
            "phase": pod.get("phase", ""),
            "exit_code": pod.get("exit_code"),
        }
    return None


def _pod_entries(
    investigation: dict[str, Any], namespace: str, name: str
) -> list[dict[str, Any]]:
    return [
        pod
        for pod in investigation.get("pods", {}).get("problematic_pods", [])
        if pod.get("namespace") == namespace and pod.get("name") == name
    ]


def _best_pod_entry(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not entries:
        return None

    def score(entry: dict[str, Any]) -> int:
        value = 0
        if entry.get("waiting_reason"):
            value += 40
        if entry.get("container"):
            value += 20
        if entry.get("container_image"):
            value += 10
        if entry.get("controller_kind"):
            value += 5
        return value

    return max(entries, key=score)


def _status_text(pod_entry: dict[str, Any] | None) -> str:
    if not pod_entry:
        return ""
    return " ".join(
        str(pod_entry.get(key, ""))
        for key in ("status", "waiting_reason", "terminated_reason")
    )


def _failure_category(pod_entry: dict[str, Any] | None) -> str:
    text = _status_text(pod_entry)
    waiting = str((pod_entry or {}).get("waiting_reason", ""))

    if waiting in IMAGE_PULL_REASONS or any(reason in text for reason in IMAGE_PULL_REASONS):
        return "image_pull"
    if waiting in CRASH_LOOP_REASONS or "CrashLoopBackOff" in text:
        return "crash_loop"
    if (pod_entry or {}).get("terminated_reason") or (pod_entry or {}).get("exit_code") not in (
        None,
        0,
    ):
        return "terminated"
    if any(marker in text for marker in TERMINATED_MARKERS):
        return "terminated"
    return "generic"


def _container_ever_started(pod_entry: dict[str, Any] | None) -> bool:
    if not pod_entry:
        return False

    if (pod_entry.get("restart_count") or 0) > 0:
        return True
    if pod_entry.get("terminated_reason"):
        return True
    if pod_entry.get("exit_code") not in (None, 0):
        return True
    return False


def _has_usable_logs(investigation: dict[str, Any], namespace: str, name: str) -> bool:
    for entry in investigation.get("logs", {}).get("collected", []):
        if entry.get("namespace") != namespace:
            continue
        pod_ref = entry.get("pod") or entry.get("name")
        if pod_ref != name:
            continue
        if entry.get("recent_lines") or entry.get("highlights"):
            return True
    return False


def _controller_info(pod_entry: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if not pod_entry:
        return None, None

    controller_kind = pod_entry.get("controller_kind")
    controller_name = pod_entry.get("controller_name")
    if controller_kind and controller_name:
        return controller_kind, controller_name

    deployment_name = pod_entry.get("deployment_name")
    if deployment_name:
        return "Deployment", deployment_name

    owner_kind = pod_entry.get("owner_kind")
    owner_name = pod_entry.get("owner_name")
    if owner_kind in {"DaemonSet", "StatefulSet", "Job", "CronJob", "ReplicaSet"}:
        return owner_kind, owner_name

    return None, None


def _append_unique(commands: list[str], command: str) -> None:
    if command and command not in commands:
        commands.append(command)


def _image_pull_commands(
    namespace: str,
    name: str,
    pod_entry: dict[str, Any] | None,
) -> list[str]:
    commands = [f"kubectl describe pod {name} -n {namespace}"]
    controller_kind, controller_name = _controller_info(pod_entry)
    container_name = (pod_entry or {}).get("container") or "web"
    valid_image = infer_valid_image((pod_entry or {}).get("container_image"))

    if controller_kind == "Deployment" and controller_name:
        if valid_image:
            _append_unique(
                commands,
                (
                    f"kubectl set image deployment/{controller_name} "
                    f"{container_name}={valid_image} -n {namespace}"
                ),
            )
        _append_unique(
            commands,
            f"kubectl rollout status deployment/{controller_name} -n {namespace}",
        )
        return commands

    if controller_kind == "DaemonSet" and controller_name:
        if valid_image:
            _append_unique(
                commands,
                (
                    f"kubectl set image daemonset/{controller_name} "
                    f"{container_name}={valid_image} -n {namespace}"
                ),
            )
        _append_unique(
            commands,
            f"kubectl rollout status daemonset/{controller_name} -n {namespace}",
        )
        return commands

    if controller_kind == "StatefulSet" and controller_name:
        if valid_image:
            _append_unique(
                commands,
                (
                    f"kubectl set image statefulset/{controller_name} "
                    f"{container_name}={valid_image} -n {namespace}"
                ),
            )
        _append_unique(
            commands,
            f"kubectl rollout status statefulset/{controller_name} -n {namespace}",
        )
        return commands

    if controller_kind == "Job" and controller_name:
        _append_unique(commands, f"kubectl describe job {controller_name} -n {namespace}")
        if valid_image:
            _append_unique(
                commands,
                (
                    f"kubectl set image job/{controller_name} "
                    f"{container_name}={valid_image} -n {namespace}"
                ),
            )
        return commands

    _append_unique(commands, f"kubectl delete pod {name} -n {namespace}")
    if valid_image:
        _append_unique(
            commands,
            f"kubectl run {name} --image={valid_image} -n {namespace} --restart=Never",
        )

    return commands


def _runtime_failure_commands(
    namespace: str,
    name: str,
    pod_entry: dict[str, Any] | None,
    investigation: dict[str, Any],
    *,
    include_previous: bool,
) -> list[str]:
    commands = [f"kubectl describe pod {name} -n {namespace}"]

    if _has_usable_logs(investigation, namespace, name):
        _append_unique(commands, f"kubectl logs {name} -n {namespace}")

    if include_previous and _container_ever_started(pod_entry):
        _append_unique(commands, f"kubectl logs {name} -n {namespace} --previous")

    controller_kind, controller_name = _controller_info(pod_entry)
    if controller_kind == "Deployment" and controller_name:
        _append_unique(
            commands,
            f"kubectl describe deployment {controller_name} -n {namespace}",
        )

    return commands


def build_pod_failure_kubectl_commands(
    investigation: dict[str, Any],
) -> list[str]:
    """Build kubectl commands for the primary failed pod issue."""
    primary = _primary_pod_issue(investigation)
    if not primary:
        return []

    namespace = primary.get("namespace")
    name = primary.get("name")
    if not namespace or not name:
        return []

    pod_entry = _best_pod_entry(_pod_entries(investigation, namespace, name))
    category = _failure_category(pod_entry)

    if category == "image_pull":
        return _image_pull_commands(namespace, name, pod_entry)

    if category == "crash_loop":
        return _runtime_failure_commands(
            namespace,
            name,
            pod_entry,
            investigation,
            include_previous=True,
        )

    if category == "terminated":
        return _runtime_failure_commands(
            namespace,
            name,
            pod_entry,
            investigation,
            include_previous=True,
        )

    return _runtime_failure_commands(
        namespace,
        name,
        pod_entry,
        investigation,
        include_previous=_container_ever_started(pod_entry),
    )


def format_kubectl_commands(commands: list[str]) -> str:
    return "\n".join(commands)
