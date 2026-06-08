from ai.kubectl_commands import (
    build_pod_failure_kubectl_commands,
    infer_valid_image,
)
from services.finding_prioritizer import enrich_investigation_priorities


def _investigation_with_nginx_crash() -> dict:
    investigation = {
        "pods": {
            "problematic_pods": [
                {
                    "name": "nginx-crash",
                    "namespace": "default",
                    "status": "Container exited with code 1",
                    "phase": "Failed",
                    "exit_code": 1,
                    "terminated_reason": "Error",
                },
                {
                    "name": "kube-proxy-gbgnd",
                    "namespace": "kube-system",
                    "status": "High restart count (250)",
                    "phase": "Running",
                    "restart_count": 250,
                },
            ]
        },
        "logs": {"collected": []},
        "deployments": {"problematic_deployments": []},
    }
    return enrich_investigation_priorities(investigation)


def _standalone_image_pull_investigation() -> dict:
    investigation = {
        "pods": {
            "problematic_pods": [
                {
                    "name": "nginx-imagepullbackoff",
                    "namespace": "default",
                    "status": "ImagePullBackOff",
                    "phase": "Pending",
                    "waiting_reason": "ImagePullBackOff",
                    "container": "nginx-imagepullbackoff",
                    "container_image": "nginx:does-not-exist-12345",
                    "restart_count": 0,
                }
            ]
        },
        "logs": {
            "collected": [
                {
                    "pod": "nginx-imagepullbackoff",
                    "namespace": "default",
                    "highlights": [],
                    "recent_lines": [],
                    "message": "No logs available for this pod",
                }
            ]
        },
        "deployments": {"problematic_deployments": []},
    }
    return enrich_investigation_priorities(investigation)


def _deployment_image_pull_investigation() -> dict:
    investigation = {
        "pods": {
            "problematic_pods": [
                {
                    "name": "imagepull-demo-abc123",
                    "namespace": "ai-agent-test",
                    "status": "ErrImagePull",
                    "phase": "Pending",
                    "waiting_reason": "ErrImagePull",
                    "container": "web",
                    "container_image": "nginx:does-not-exist-12345",
                    "controller_kind": "Deployment",
                    "controller_name": "imagepull-demo",
                    "owner_kind": "ReplicaSet",
                    "owner_name": "imagepull-demo-abc123",
                    "deployment_name": "imagepull-demo",
                    "restart_count": 0,
                }
            ]
        },
        "logs": {"collected": []},
        "deployments": {"problematic_deployments": []},
    }
    return enrich_investigation_priorities(investigation)


def _crash_loop_investigation() -> dict:
    investigation = {
        "pods": {
            "problematic_pods": [
                {
                    "name": "crashloop-demo",
                    "namespace": "default",
                    "status": "CrashLoopBackOff",
                    "phase": "Running",
                    "waiting_reason": "CrashLoopBackOff",
                    "container": "app",
                    "restart_count": 6,
                }
            ]
        },
        "logs": {
            "collected": [
                {
                    "pod": "crashloop-demo",
                    "namespace": "default",
                    "recent_lines": ["fatal: startup failed"],
                    "highlights": ["fatal: startup failed"],
                }
            ]
        },
        "deployments": {"problematic_deployments": []},
    }
    return enrich_investigation_priorities(investigation)


def test_infer_valid_image_for_known_bad_nginx_tag():
    assert infer_valid_image("nginx:does-not-exist-12345") == "nginx:latest"


def test_standalone_image_pull_backoff_commands():
    investigation = _standalone_image_pull_investigation()
    commands = build_pod_failure_kubectl_commands(investigation)

    assert commands[:2] == [
        "kubectl describe pod nginx-imagepullbackoff -n default",
        "kubectl delete pod nginx-imagepullbackoff -n default",
    ]
    assert not any("logs" in command for command in commands)


def test_standalone_image_pull_without_known_fix_skips_recreate():
    investigation = _standalone_image_pull_investigation()
    investigation["pods"]["problematic_pods"][0]["container_image"] = "private.registry.example/app:missing"

    commands = build_pod_failure_kubectl_commands(investigation)

    assert commands == [
        "kubectl describe pod nginx-imagepullbackoff -n default",
        "kubectl delete pod nginx-imagepullbackoff -n default",
    ]


def test_deployment_owned_image_pull_commands():
    investigation = _deployment_image_pull_investigation()
    commands = build_pod_failure_kubectl_commands(investigation)

    assert commands == [
        "kubectl describe pod imagepull-demo-abc123 -n ai-agent-test",
        "kubectl set image deployment/imagepull-demo web=nginx:latest -n ai-agent-test",
        "kubectl rollout status deployment/imagepull-demo -n ai-agent-test",
    ]
    assert not any("logs" in command for command in commands)


def test_crash_loop_backoff_includes_logs_and_previous():
    investigation = _crash_loop_investigation()
    commands = build_pod_failure_kubectl_commands(investigation)

    assert commands == [
        "kubectl describe pod crashloop-demo -n default",
        "kubectl logs crashloop-demo -n default",
        "kubectl logs crashloop-demo -n default --previous",
    ]


def test_build_commands_for_failed_user_pod_includes_describe_and_logs():
    investigation = _investigation_with_nginx_crash()
    commands = build_pod_failure_kubectl_commands(investigation)

    assert commands == [
        "kubectl describe pod nginx-crash -n default",
        "kubectl logs nginx-crash -n default --previous",
    ]


def test_build_commands_include_deployment_when_managed():
    investigation = _investigation_with_nginx_crash()
    investigation["pods"]["problematic_pods"][0]["controller_kind"] = "Deployment"
    investigation["pods"]["problematic_pods"][0]["controller_name"] = "nginx-demo"
    investigation["pods"]["problematic_pods"][0]["deployment_name"] = "nginx-demo"
    commands = build_pod_failure_kubectl_commands(investigation)

    assert "kubectl describe deployment nginx-demo -n default" in commands


def test_primary_issue_follows_user_workload_priority():
    investigation = _investigation_with_nginx_crash()
    commands = build_pod_failure_kubectl_commands(investigation)

    assert commands[0] == "kubectl describe pod nginx-crash -n default"
    assert "kube-proxy" not in commands[0]
