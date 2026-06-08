"""Beginner-friendly Kubernetes error messages."""

from kubernetes.executor import KubectlResult


def is_connection_error(message: str) -> bool:
    lowered = message.lower()
    markers = (
        "unable to connect",
        "connection refused",
        "tls handshake timeout",
        "no such host",
        "context was not found",
        "current-context is not set",
        "kubeconfig",
        "not found in path",
        "timed out",
        "timeout",
        "forbidden",
        "unauthorized",
    )
    return any(marker in lowered for marker in markers)


def friendly_kubectl_error(result: KubectlResult, *, context: str | None = None) -> str:
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    detail = stderr or stdout or f"Command failed with exit code {result.return_code}"

    if result.return_code == 127 or "kubectl not found" in detail.lower():
        return (
            "kubectl is not available in the backend container.\n\n"
            "Please verify kubectl is installed in the backend image."
        )

    if "current-context is not set" in detail.lower() or "context was not found" in detail.lower():
        target = f" '{context}'" if context else ""
        return (
            f"Kubernetes context{target} was not found in your kubeconfig.\n\n"
            "Please verify:\n"
            "- kubeconfig path is correct\n"
            "- the selected cluster context exists\n"
            "- you selected a valid cluster in the dashboard"
        )

    if is_connection_error(detail):
        target = f" ({context})" if context else ""
        return (
            f"Unable to connect to Kubernetes cluster{target}.\n\n"
            "Please verify:\n"
            "- kubeconfig path\n"
            "- cluster API server is reachable from the backend\n"
            "- kubectl permissions\n"
            "- VPN or network access to the cluster"
        )

    return detail


def cluster_unreachable_message(context: str | None = None) -> str:
    target = f" '{context}'" if context else ""
    return (
        f"Unable to connect to Kubernetes cluster{target}.\n\n"
        "Please verify:\n"
        "- kubeconfig path\n"
        "- cluster access\n"
        "- kubectl permissions"
    )
