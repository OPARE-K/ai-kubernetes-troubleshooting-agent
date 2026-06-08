from typing import Any

from kubernetes.executor import KubectlExecutor


class DeploymentInspector:
    """Inspect deployments for rollout and replica issues."""

    def __init__(self, executor: KubectlExecutor) -> None:
        self.executor = executor

    def inspect(self) -> dict[str, Any]:
        result = self.executor.run("get", "deployments", "-A", "-o", "json")

        if not result.success:
            return {
                "healthy": False,
                "error": result.stderr or "Failed to fetch deployments",
                "total_deployments": 0,
                "problematic_deployments": [],
            }

        data = result.json_output()
        if not isinstance(data, dict):
            return {
                "healthy": False,
                "error": "Unexpected kubectl response format",
                "total_deployments": 0,
                "problematic_deployments": [],
            }

        items = data.get("items", [])
        problematic: list[dict[str, Any]] = []

        for deployment in items:
            metadata = deployment.get("metadata", {})
            name = metadata.get("name", "unknown")
            namespace = metadata.get("namespace", "default")
            status = deployment.get("status", {})
            spec = deployment.get("spec", {})

            desired = spec.get("replicas", 0) or 0
            available = status.get("availableReplicas", 0) or 0
            unavailable = status.get("unavailableReplicas", 0) or 0
            ready = status.get("readyReplicas", 0) or 0
            conditions = status.get("conditions", [])

            failed_conditions = [
                {
                    "type": condition.get("type", "Unknown"),
                    "status": condition.get("status", "Unknown"),
                    "reason": condition.get("reason", ""),
                    "message": condition.get("message", ""),
                }
                for condition in conditions
                if condition.get("status") != "True"
            ]

            rollout_failed = any(
                condition.get("type") == "Progressing"
                and condition.get("status") == "False"
                for condition in conditions
            )

            is_unhealthy = (
                (desired > 0 and available < desired)
                or unavailable > 0
                or rollout_failed
                or bool(failed_conditions)
            )

            if is_unhealthy:
                problematic.append(
                    {
                        "name": name,
                        "namespace": namespace,
                        "desired_replicas": desired,
                        "available_replicas": available,
                        "ready_replicas": ready,
                        "unavailable_replicas": unavailable,
                        "rollout_failed": rollout_failed,
                        "conditions": failed_conditions,
                    }
                )

        return {
            "healthy": len(problematic) == 0,
            "total_deployments": len(items),
            "problematic_deployments": problematic,
        }
