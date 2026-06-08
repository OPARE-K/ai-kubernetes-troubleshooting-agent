from typing import Any

from ai.kubectl_commands import (
    build_pod_failure_kubectl_commands,
    format_kubectl_commands,
)


class FixRecommendationEngine:
    """Format and validate actionable Kubernetes fix recommendations."""

    def build(
        self, parsed_llm: dict[str, Any], investigation: dict[str, Any]
    ) -> dict[str, str | list[str]]:
        fix = str(parsed_llm.get("fix", "")).strip()
        kubectl_command = self._normalize_kubectl_command(
            str(parsed_llm.get("kubectl_command", "")).strip()
        )
        prevention = str(parsed_llm.get("prevention_recommendation", "")).strip()

        pod_commands = build_pod_failure_kubectl_commands(investigation)
        if pod_commands:
            kubectl_command = format_kubectl_commands(pod_commands)
        elif not kubectl_command:
            kubectl_command = self._fallback_kubectl_command(investigation)
            pod_commands = (
                [kubectl_command] if kubectl_command else []
            )

        if not fix:
            fix = "Review the identified root cause and apply the recommended cluster changes."

        if not prevention:
            prevention = (
                "Add readiness/liveness probes, validate configuration in CI, "
                "and monitor pod restart counts and deployment availability."
            )

        return {
            "fix": fix,
            "kubectl_command": kubectl_command,
            "kubectl_commands": pod_commands or ([kubectl_command] if kubectl_command else []),
            "prevention_recommendation": prevention,
        }

    def _normalize_kubectl_command(self, command: str) -> str:
        if not command:
            return ""

        normalized = command.strip().strip("`")
        if not normalized.startswith("kubectl"):
            normalized = f"kubectl {normalized}"

        return normalized

    def _fallback_kubectl_command(self, investigation: dict[str, Any]) -> str:
        commands = build_pod_failure_kubectl_commands(investigation)
        if commands:
            return format_kubectl_commands(commands)

        deployments = investigation.get("deployments", {}).get(
            "problematic_deployments", []
        )
        if deployments:
            deployment = deployments[0]
            return (
                f"kubectl describe deployment {deployment['name']} "
                f"-n {deployment['namespace']}"
            )

        pods = investigation.get("pods", {}).get("problematic_pods", [])
        if pods:
            pod = pods[0]
            return f"kubectl describe pod {pod['name']} -n {pod['namespace']}"

        return "kubectl get pods -A"
