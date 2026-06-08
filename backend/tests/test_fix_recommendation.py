from ai.fix_recommendation import FixRecommendationEngine
from services.finding_prioritizer import enrich_investigation_priorities


def test_fix_engine_always_populates_pod_failure_commands():
    investigation = enrich_investigation_priorities(
        {
            "pods": {
                "problematic_pods": [
                    {
                        "name": "nginx-crash",
                        "namespace": "default",
                        "status": "Container exited with code 1",
                        "phase": "Failed",
                        "exit_code": 1,
                    }
                ]
            },
            "logs": {"collected": []},
            "deployments": {"problematic_deployments": []},
        }
    )

    result = FixRecommendationEngine().build(
        {
            "fix": "Fix the crash command.",
            "kubectl_command": "",
            "prevention_recommendation": "",
        },
        investigation,
    )

    assert result["kubectl_command"]
    assert "kubectl describe pod nginx-crash -n default" in result["kubectl_command"]
    assert "kubectl logs nginx-crash -n default --previous" in result["kubectl_command"]
    assert result["kubectl_commands"]
