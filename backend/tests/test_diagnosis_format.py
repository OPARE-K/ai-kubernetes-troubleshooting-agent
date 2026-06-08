from services.diagnosis_format import (
    build_ai_unavailable_diagnosis,
    compute_fallback_confidence,
    finalize_diagnosis,
)
from services.finding_prioritizer import (
    build_deterministic_diagnosis,
    enrich_investigation_priorities,
)


def _nginx_crash_investigation() -> dict:
    investigation = {
        "pods": {
            "problematic_pods": [
                {
                    "name": "nginx-crash",
                    "namespace": "default",
                    "status": "Error",
                    "phase": "Failed",
                    "terminated_reason": "Error",
                    "exit_code": 1,
                }
            ]
        },
        "logs": {"collected": []},
        "deployments": {"problematic_deployments": []},
    }
    return enrich_investigation_priorities(investigation)


def test_compute_fallback_confidence_for_strong_evidence():
    investigation = _nginx_crash_investigation()
    assert compute_fallback_confidence(investigation) == 88


def test_finalize_diagnosis_populates_commands_and_confidence():
    investigation = _nginx_crash_investigation()
    diagnosis = finalize_diagnosis(
        {
            "root_cause": "User workload pod default/nginx-crash failed",
            "explanation": "Evidence-based fallback diagnosis.",
            "fix": "Inspect the pod.",
            "kubectl_command": (
                "kubectl describe pod nginx-crash -n default "
                "kubectl logs nginx-crash -n default --previous"
            ),
        },
        investigation,
    )

    assert diagnosis["confidence"] == 88
    assert diagnosis["kubectl_commands"] == [
        "kubectl describe pod nginx-crash -n default",
        "kubectl logs nginx-crash -n default --previous",
    ]
    assert "\n" in diagnosis["kubectl_command"]


def _generic_fallback(reason: str) -> dict:
    return {
        "root_cause": "AI diagnosis unavailable",
        "explanation": reason,
        "fix": "Retry later.",
        "kubectl_command": "",
        "kubectl_commands": [],
        "prevention_recommendation": "",
        "confidence": 0,
        "confidence_reasoning": "AI reasoning did not complete successfully.",
    }


def test_ai_unavailable_diagnosis_keeps_nginx_crash_fallback():
    investigation = _nginx_crash_investigation()
    diagnosis = build_ai_unavailable_diagnosis(
        investigation,
        "OpenRouter rate limited (429): too many requests",
        build_deterministic_diagnosis=build_deterministic_diagnosis,
        generic_fallback_diagnosis=_generic_fallback,
    )

    assert "nginx-crash" in diagnosis["root_cause"]
    assert diagnosis["confidence"] == 88
    assert diagnosis["kubectl_commands"] == [
        "kubectl describe pod nginx-crash -n default",
        "kubectl logs nginx-crash -n default --previous",
    ]
