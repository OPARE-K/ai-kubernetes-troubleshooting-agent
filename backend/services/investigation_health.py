from typing import Any

from services.k8s_errors import is_connection_error


def collect_warnings(investigation_data: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for section in ("pods", "events", "deployments", "network"):
        error = investigation_data.get(section, {}).get("error")
        if error:
            warnings.append(f"{section}: {error}")
    return warnings


def has_connection_failure(investigation_data: dict[str, Any]) -> bool:
    for section in ("pods", "events", "deployments", "network"):
        error = investigation_data.get(section, {}).get("error", "")
        if error and is_connection_error(str(error)):
            return True
    return False


def is_cluster_healthy(investigation_data: dict[str, Any]) -> bool:
    if has_connection_failure(investigation_data):
        return False

    pods = investigation_data.get("pods", {})
    deployments = investigation_data.get("deployments", {})
    events = investigation_data.get("events", {})
    network = investigation_data.get("network", {})

    if pods.get("problematic_pods"):
        return False
    if deployments.get("problematic_deployments"):
        return False
    if events.get("findings"):
        return False
    if network.get("findings"):
        return False
    return True
