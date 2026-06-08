from typing import Any

from kubernetes.executor import KubectlExecutor

DNS_COMPONENT_LABELS = {
    "k8s-app": {"kube-dns", "coredns"},
    "app.kubernetes.io/name": {"coredns"},
}


class NetworkInspector:
    """Inspect services, endpoints, and basic DNS health."""

    def __init__(self, executor: KubectlExecutor) -> None:
        self.executor = executor

    def inspect(self) -> dict[str, Any]:
        services_result = self.executor.run("get", "svc", "-A", "-o", "json")
        endpoints_result = self.executor.run("get", "endpoints", "-A", "-o", "json")
        pods_result = self.executor.run("get", "pods", "-A", "-o", "json")

        if not services_result.success:
            return {
                "healthy": False,
                "error": services_result.stderr or "Failed to fetch services",
                "findings": [],
            }

        services_data = services_result.json_output()
        endpoints_data = (
            endpoints_result.json_output() if endpoints_result.success else {"items": []}
        )
        pods_data = pods_result.json_output() if pods_result.success else {"items": []}

        if not isinstance(services_data, dict):
            return {
                "healthy": False,
                "error": "Unexpected services response format",
                "findings": [],
            }

        endpoints_by_key = self._index_endpoints(endpoints_data)
        pods_by_namespace = self._index_pods_by_namespace(pods_data)
        findings: list[dict[str, str]] = []

        for service in services_data.get("items", []):
            metadata = service.get("metadata", {})
            spec = service.get("spec", {})
            name = metadata.get("name", "unknown")
            namespace = metadata.get("namespace", "default")
            service_type = spec.get("type", "ClusterIP")
            selector = spec.get("selector") or {}

            if service_type == "ExternalName":
                continue

            endpoint_key = (namespace, name)
            endpoint_addresses = endpoints_by_key.get(endpoint_key, 0)

            if endpoint_addresses == 0 and selector:
                findings.append(
                    {
                        "type": "missing_endpoints",
                        "service": name,
                        "namespace": namespace,
                        "message": f"Service '{name}' has no ready endpoints",
                    }
                )

                if not self._selector_matches_pods(selector, pods_by_namespace.get(namespace, [])):
                    findings.append(
                        {
                            "type": "selector_mismatch",
                            "service": name,
                            "namespace": namespace,
                            "message": (
                                f"Service '{name}' selector does not match any pod labels "
                                f"in namespace '{namespace}'"
                            ),
                        }
                    )

        dns_findings = self._check_dns_health(pods_data if isinstance(pods_data, dict) else {})
        findings.extend(dns_findings)

        return {
            "healthy": len(findings) == 0,
            "services_checked": len(services_data.get("items", [])),
            "findings": findings,
        }

    def _index_endpoints(self, endpoints_data: Any) -> dict[tuple[str, str], int]:
        indexed: dict[tuple[str, str], int] = {}
        if not isinstance(endpoints_data, dict):
            return indexed

        for endpoint in endpoints_data.get("items", []):
            metadata = endpoint.get("metadata", {})
            namespace = metadata.get("namespace", "default")
            name = metadata.get("name", "unknown")
            address_count = 0

            for subset in endpoint.get("subsets", []):
                address_count += len(subset.get("addresses", []))

            indexed[(namespace, name)] = address_count

        return indexed

    def _index_pods_by_namespace(
        self, pods_data: Any
    ) -> dict[str, list[dict[str, str]]]:
        indexed: dict[str, list[dict[str, str]]] = {}
        if not isinstance(pods_data, dict):
            return indexed

        for pod in pods_data.get("items", []):
            metadata = pod.get("metadata", {})
            namespace = metadata.get("namespace", "default")
            labels = metadata.get("labels", {})
            indexed.setdefault(namespace, []).append(labels)

        return indexed

    def _selector_matches_pods(
        self, selector: dict[str, str], pod_labels_list: list[dict[str, str]]
    ) -> bool:
        if not selector:
            return False

        for labels in pod_labels_list:
            if all(labels.get(key) == value for key, value in selector.items()):
                return True
        return False

    def _check_dns_health(self, pods_data: dict[str, Any]) -> list[dict[str, str]]:
        findings: list[dict[str, str]] = []
        dns_pods: list[dict[str, str]] = []

        for pod in pods_data.get("items", []):
            metadata = pod.get("metadata", {})
            labels = metadata.get("labels", {})
            phase = pod.get("status", {}).get("phase", "Unknown")

            if self._is_dns_pod(labels):
                dns_pods.append(
                    {
                        "name": metadata.get("name", "unknown"),
                        "namespace": metadata.get("namespace", "kube-system"),
                        "phase": phase,
                    }
                )

        if not dns_pods:
            findings.append(
                {
                    "type": "dns_related",
                    "service": "coredns/kube-dns",
                    "namespace": "kube-system",
                    "message": "No CoreDNS or kube-dns pods detected in the cluster",
                }
            )
            return findings

        unhealthy_dns = [pod for pod in dns_pods if pod["phase"] != "Running"]
        for pod in unhealthy_dns:
            findings.append(
                {
                    "type": "dns_related",
                    "service": pod["name"],
                    "namespace": pod["namespace"],
                    "message": f"DNS pod '{pod['name']}' is in phase '{pod['phase']}'",
                }
            )

        return findings

    def _is_dns_pod(self, labels: dict[str, str]) -> bool:
        for label_key, expected_values in DNS_COMPONENT_LABELS.items():
            if labels.get(label_key) in expected_values:
                return True
        return False
