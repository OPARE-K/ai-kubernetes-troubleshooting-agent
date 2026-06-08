import re
from datetime import datetime, timezone
from typing import Any

from kubernetes.executor import KubectlExecutor
from loguru import logger

UNHEALTHY_WAITING_REASONS = {
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "CreateContainerConfigError",
    "CreateContainerError",
    "RunContainerError",
    "InvalidImageName",
    "ContainerCannotRun",
}

UNHEALTHY_TERMINATED_REASONS = {
    "Error",
    "OOMKilled",
    "ContainerCannotRun",
    "DeadlineExceeded",
}

UNHEALTHY_PHASES = {
    "Failed",
    "Unknown",
}

STUCK_CONTAINER_CREATING = "ContainerCreating"
HIGH_RESTART_THRESHOLD = 5
PENDING_TOO_LONG_SECONDS = 300


class PodInspector:
    """Inspect pod health and detect unhealthy workloads across all namespaces."""

    def __init__(self, executor: KubectlExecutor) -> None:
        self.executor = executor

    def inspect(self) -> dict[str, Any]:
        result = self.executor.run("get", "pods", "-A", "-o", "json")

        if not result.success:
            return {
                "healthy": False,
                "error": result.stderr or "Failed to fetch pods",
                "total_pods": 0,
                "problematic_pods": [],
            }

        data = result.json_output()
        if not isinstance(data, dict):
            return {
                "healthy": False,
                "error": "Unexpected kubectl response format",
                "total_pods": 0,
                "problematic_pods": [],
            }

        items = data.get("items", [])
        problematic_pods: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()

        logger.info(f"Pod scan started — {len(items)} pod(s) across all namespaces")

        for pod in items:
            metadata = pod.get("metadata", {})
            deployment_name = self._deployment_name_for_pod(metadata)
            pod_context = {
                "deployment_name": deployment_name,
                **self._controller_fields(metadata),
                "container_images": {
                    container.get("name", ""): container.get("image", "")
                    for container in pod.get("spec", {}).get("containers", [])
                },
            }
            self._inspect_pod(pod, problematic_pods, seen, pod_context)

        logger.info(
            f"Pod scan complete — {len(items)} scanned, "
            f"{len(problematic_pods)} problematic pod(s) found"
        )
        for entry in problematic_pods:
            logger.warning(
                "Problematic pod: {namespace}/{name} — {reason} "
                "(phase={phase}, container={container}, restarts={restarts})",
                namespace=entry.get("namespace"),
                name=entry.get("name"),
                reason=entry.get("status"),
                phase=entry.get("phase"),
                container=entry.get("container", "n/a"),
                restarts=entry.get("restart_count", 0),
            )

        return {
            "healthy": len(problematic_pods) == 0,
            "total_pods": len(items),
            "problematic_pods": problematic_pods,
        }

    @staticmethod
    def _deployment_name_for_pod(metadata: dict[str, Any]) -> str | None:
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

    @staticmethod
    def _controller_fields(metadata: dict[str, Any]) -> dict[str, str | None]:
        owner_refs = metadata.get("ownerReferences", [])
        owner_kind = owner_refs[0].get("kind") if owner_refs else None
        owner_name = owner_refs[0].get("name") if owner_refs else None

        deployment_name = PodInspector._deployment_name_for_pod(metadata)
        if deployment_name:
            return {
                "owner_kind": owner_kind,
                "owner_name": owner_name,
                "controller_kind": "Deployment",
                "controller_name": deployment_name,
            }

        for ref in owner_refs:
            kind = ref.get("kind")
            if kind in {"DaemonSet", "StatefulSet", "Job", "CronJob", "ReplicaSet"}:
                return {
                    "owner_kind": owner_kind,
                    "owner_name": owner_name,
                    "controller_kind": kind,
                    "controller_name": ref.get("name"),
                }

        return {
            "owner_kind": owner_kind,
            "owner_name": owner_name,
            "controller_kind": None,
            "controller_name": None,
        }

    def _inspect_pod(
        self,
        pod: dict[str, Any],
        problematic_pods: list[dict[str, Any]],
        seen: set[tuple[str, str, str]],
        pod_context: dict[str, Any],
    ) -> None:
        metadata = pod.get("metadata", {})
        status = pod.get("status", {})
        name = metadata.get("name", "unknown")
        namespace = metadata.get("namespace", "default")
        phase = status.get("phase", "Unknown")
        created_at = metadata.get("creationTimestamp")

        if phase in UNHEALTHY_PHASES:
            reason = status.get("reason", phase)
            self._add_problematic(
                problematic_pods,
                seen,
                name=name,
                namespace=namespace,
                reason=reason,
                phase=phase,
                pod_context=pod_context,
            )

        if status.get("reason") == "Evicted":
            self._add_problematic(
                problematic_pods,
                seen,
                name=name,
                namespace=namespace,
                reason="Evicted",
                phase=phase,
                message=status.get("message", ""),
                pod_context=pod_context,
            )

        if phase == "Pending":
            has_unhealthy_containers = any(
                (cs.get("state", {}).get("waiting", {}) or {}).get("reason")
                in UNHEALTHY_WAITING_REASONS
                for cs in (
                    status.get("containerStatuses", [])
                    + status.get("initContainerStatuses", [])
                )
            )
            if has_unhealthy_containers or self._pending_too_long(created_at):
                reason = (
                    "Pending with container errors"
                    if has_unhealthy_containers
                    else "Pending too long"
                )
                self._add_problematic(
                    problematic_pods,
                    seen,
                    name=name,
                    namespace=namespace,
                    reason=reason,
                    phase=phase,
                    pod_context=pod_context,
                )

        spec_containers = {
            c.get("name", "unknown") for c in pod.get("spec", {}).get("containers", [])
        }
        status_containers = {
            c.get("name", "unknown")
            for c in status.get("containerStatuses", [])
        }
        missing_status = spec_containers - status_containers
        for container_name in missing_status:
            self._add_problematic(
                problematic_pods,
                seen,
                name=name,
                namespace=namespace,
                reason="Container status missing",
                phase=phase,
                container=container_name,
                pod_context=pod_context,
            )

        for container_status in status.get("containerStatuses", []):
            self._inspect_container_status(
                problematic_pods,
                seen,
                name,
                namespace,
                phase,
                container_status,
                is_init=False,
                pod_context=pod_context,
            )

        for container_status in status.get("initContainerStatuses", []):
            self._inspect_container_status(
                problematic_pods,
                seen,
                name,
                namespace,
                phase,
                container_status,
                is_init=True,
                pod_context=pod_context,
            )

    def _inspect_container_status(
        self,
        problematic_pods: list[dict[str, Any]],
        seen: set[tuple[str, str, str]],
        name: str,
        namespace: str,
        phase: str,
        container_status: dict[str, Any],
        *,
        is_init: bool,
        pod_context: dict[str, Any],
    ) -> None:
        container_name = container_status.get("name", "unknown")
        container_image = pod_context.get("container_images", {}).get(container_name, "")
        restart_count = container_status.get("restartCount", 0) or 0
        ready = container_status.get("ready", False)
        state = container_status.get("state", {})
        prefix = "Init: " if is_init else ""

        if restart_count >= HIGH_RESTART_THRESHOLD:
            self._add_problematic(
                problematic_pods,
                seen,
                name=name,
                namespace=namespace,
                reason=f"{prefix}High restart count ({restart_count})",
                phase=phase,
                container=container_name,
                restart_count=restart_count,
                pod_context=pod_context,
                container_image=container_image,
            )

        if not ready and phase == "Running":
            self._add_problematic(
                problematic_pods,
                seen,
                name=name,
                namespace=namespace,
                reason=f"{prefix}Container not ready",
                phase=phase,
                container=container_name,
                restart_count=restart_count,
                pod_context=pod_context,
                container_image=container_image,
            )

        waiting = state.get("waiting")
        if waiting:
            reason = waiting.get("reason", "Waiting")
            message = waiting.get("message", "")
            if reason in UNHEALTHY_WAITING_REASONS:
                self._add_problematic(
                    problematic_pods,
                    seen,
                    name=name,
                    namespace=namespace,
                    reason=f"{prefix}{reason}",
                    phase=phase,
                    container=container_name,
                    restart_count=restart_count,
                    waiting_reason=reason,
                    message=message,
                    pod_context=pod_context,
                    container_image=container_image,
                )
            elif reason == STUCK_CONTAINER_CREATING:
                self._add_problematic(
                    problematic_pods,
                    seen,
                    name=name,
                    namespace=namespace,
                    reason=f"{prefix}ContainerCreating (stuck)",
                    phase=phase,
                    container=container_name,
                    restart_count=restart_count,
                    waiting_reason=reason,
                    message=message,
                    pod_context=pod_context,
                    container_image=container_image,
                )

        terminated = state.get("terminated")
        if terminated:
            reason = terminated.get("reason", "Terminated")
            message = terminated.get("message", "")
            exit_code = terminated.get("exitCode")
            if reason in UNHEALTHY_TERMINATED_REASONS:
                self._add_problematic(
                    problematic_pods,
                    seen,
                    name=name,
                    namespace=namespace,
                    reason=f"{prefix}{reason}",
                    phase=phase,
                    container=container_name,
                    restart_count=restart_count,
                    terminated_reason=reason,
                    message=message,
                    exit_code=exit_code,
                    pod_context=pod_context,
                    container_image=container_image,
                )
            elif exit_code not in (None, 0):
                self._add_problematic(
                    problematic_pods,
                    seen,
                    name=name,
                    namespace=namespace,
                    reason=f"{prefix}Container exited with code {exit_code}",
                    phase=phase,
                    container=container_name,
                    restart_count=restart_count,
                    terminated_reason=reason,
                    message=message,
                    exit_code=exit_code,
                    pod_context=pod_context,
                    container_image=container_image,
                )

    def _pending_too_long(self, created_at: str | None) -> bool:
        if not created_at:
            return True
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            age_seconds = (datetime.now(timezone.utc) - created).total_seconds()
            return age_seconds >= PENDING_TOO_LONG_SECONDS
        except ValueError:
            return True

    def _add_problematic(
        self,
        problematic_pods: list[dict[str, Any]],
        seen: set[tuple[str, str, str]],
        *,
        name: str,
        namespace: str,
        reason: str,
        phase: str,
        container: str = "",
        restart_count: int = 0,
        waiting_reason: str = "",
        terminated_reason: str = "",
        message: str = "",
        exit_code: int | None = None,
        pod_context: dict[str, Any] | None = None,
        container_image: str = "",
    ) -> None:
        key = (namespace, name, reason)
        if key in seen:
            return
        seen.add(key)
        entry: dict[str, Any] = {
            "name": name,
            "namespace": namespace,
            "status": reason,
            "phase": phase,
        }
        if container:
            entry["container"] = container
        if restart_count:
            entry["restart_count"] = restart_count
        if waiting_reason:
            entry["waiting_reason"] = waiting_reason
        if terminated_reason:
            entry["terminated_reason"] = terminated_reason
        if message:
            entry["message"] = message
        if exit_code is not None:
            entry["exit_code"] = exit_code
        if container_image:
            entry["container_image"] = container_image
        if pod_context:
            if pod_context.get("deployment_name"):
                entry["deployment_name"] = pod_context["deployment_name"]
            if pod_context.get("owner_kind"):
                entry["owner_kind"] = pod_context["owner_kind"]
            if pod_context.get("owner_name"):
                entry["owner_name"] = pod_context["owner_name"]
            if pod_context.get("controller_kind"):
                entry["controller_kind"] = pod_context["controller_kind"]
            if pod_context.get("controller_name"):
                entry["controller_name"] = pod_context["controller_name"]
        problematic_pods.append(entry)
