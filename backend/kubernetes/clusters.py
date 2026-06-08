from pathlib import Path
from typing import Any

from core.config import settings
from kubernetes.executor import KubectlExecutor
from services.k8s_errors import friendly_kubectl_error


def _executor_for_listing() -> KubectlExecutor:
    return KubectlExecutor(kubeconfig_path=settings.kubeconfig_path)


def kubeconfig_status() -> dict[str, Any]:
    path = settings.kubeconfig_path.strip()
    if not path:
        return {
            "configured": False,
            "path": "",
            "message": "KUBECONFIG_PATH is not set in backend/.env",
        }

    config_file = Path(path)
    if not config_file.is_file():
        return {
            "configured": False,
            "path": path,
            "message": f"Kubeconfig file not found at {path}",
        }

    return {"configured": True, "path": path, "message": ""}


def list_clusters() -> dict[str, Any]:
    status = kubeconfig_status()
    if not status["configured"]:
        return {
            **status,
            "current_context": None,
            "clusters": [],
        }

    executor = _executor_for_listing()
    contexts_result = executor.run("config", "get-contexts", "-o", "name", timeout=10)
    if not contexts_result.success:
        return {
            **status,
            "current_context": None,
            "clusters": [],
            "message": friendly_kubectl_error(contexts_result),
        }

    names = [line.strip() for line in contexts_result.stdout.splitlines() if line.strip()]
    current_result = executor.run("config", "current-context", timeout=10)
    current_context = current_result.stdout.strip() if current_result.success else None

    clusters: list[dict[str, Any]] = []
    for name in names:
        health = check_cluster_health(name)
        clusters.append(
            {
                "name": name,
                "is_current": name == current_context,
                "reachable": health["reachable"],
                "status_message": health["message"],
            }
        )

    return {
        **status,
        "current_context": current_context,
        "clusters": clusters,
        "message": "",
    }


def check_cluster_health(context: str) -> dict[str, Any]:
    status = kubeconfig_status()
    if not status["configured"]:
        return {
            "context": context,
            "reachable": False,
            "message": status["message"],
        }

    executor = KubectlExecutor(
        kubeconfig_path=settings.kubeconfig_path,
        context=context,
    )
    result = executor.run("get", "nodes", "--request-timeout=8s", timeout=12)
    if result.success:
        return {
            "context": context,
            "reachable": True,
            "message": "Cluster is reachable",
        }

    return {
        "context": context,
        "reachable": False,
        "message": friendly_kubectl_error(result, context=context),
    }
