import time

from fastapi import APIRouter, HTTPException

from ai.agent import diagnose_investigation
from ai.llm_client import LLMClientError
from ai.root_cause_analyzer import RootCauseAnalyzerError
from kubernetes.clusters import kubeconfig_status
from models.investigation import (
    Diagnosis,
    InvestigateRequest,
    InvestigateResponse,
    InvestigationPayload,
)
from services.investigation import InvestigationService
from services.diagnosis_format import build_ai_unavailable_diagnosis, finalize_diagnosis
from services.finding_prioritizer import build_deterministic_diagnosis
from services.investigation_health import (
    collect_warnings,
    has_connection_failure,
    is_cluster_healthy,
)
from services.investigation_store import InvestigationStore
from services.k8s_errors import cluster_unreachable_message
from services.progress_reporter import create_progress_reporter
from loguru import logger

router = APIRouter(tags=["investigation"])


def _fallback_diagnosis(reason: str) -> dict[str, str | int | list[str]]:
    return {
        "root_cause": "AI diagnosis unavailable",
        "explanation": reason,
        "fix": (
            "Review the investigation payload for Kubernetes evidence. "
            "Retry the request, or verify OPENROUTER_API_KEY and OPENROUTER_MODEL in backend/.env."
        ),
        "kubectl_command": "",
        "kubectl_commands": [],
        "prevention_recommendation": "",
        "confidence": 0,
        "confidence_reasoning": "AI reasoning did not complete successfully.",
    }


def _healthy_cluster_diagnosis() -> dict[str, str | int | list[str]]:
    commands = ["kubectl get pods -A"]
    return {
        "root_cause": "No critical Kubernetes issues detected",
        "explanation": "Cluster appears healthy based on pods, events, deployments, and networking checks.",
        "fix": "No immediate fix required. Continue monitoring the cluster.",
        "kubectl_command": commands[0],
        "kubectl_commands": commands,
        "prevention_recommendation": "Keep resource requests/limits and probes configured for workloads.",
        "confidence": 85,
        "confidence_reasoning": "No unhealthy pods, deployments, events, or networking issues were found.",
    }


@router.post("/investigate", response_model=InvestigateResponse)
def investigate_cluster(body: InvestigateRequest | None = None) -> InvestigateResponse:
    request = body or InvestigateRequest()
    investigation_start = time.perf_counter()

    config_status = kubeconfig_status()
    if not config_status["configured"]:
        raise HTTPException(status_code=503, detail=config_status["message"])

    store = InvestigationStore(request.investigation_id, request.user_id)
    store.start_investigation()
    report = create_progress_reporter(request.investigation_id, store)

    service = InvestigationService(cluster_context=request.cluster_context)
    reachable, connectivity_message = service.check_connectivity()
    if not reachable:
        store.fail_investigation(connectivity_message)
        raise HTTPException(
            status_code=503,
            detail=connectivity_message or cluster_unreachable_message(request.cluster_context),
        )

    try:
        investigation_data = service.run_investigation(on_progress=report)
    except Exception as exc:
        store.fail_investigation(str(exc))
        logger.exception("Investigation failed with unexpected error")
        raise HTTPException(
            status_code=500,
            detail=f"Investigation failed: {exc}",
        ) from exc

    investigation_elapsed = time.perf_counter() - investigation_start
    logger.info(f"Kubernetes investigation completed in {investigation_elapsed:.2f}s")

    warnings = collect_warnings(investigation_data)
    cluster_healthy = is_cluster_healthy(investigation_data)

    if has_connection_failure(investigation_data):
        message = cluster_unreachable_message(request.cluster_context)
        store.fail_investigation(message)
        raise HTTPException(status_code=503, detail=message)

    ai_start = time.perf_counter()
    report("ai_reasoning", "running")
    if cluster_healthy:
        diagnosis_data = _healthy_cluster_diagnosis()
        logger.info("No critical issues detected — using healthy-cluster diagnosis")
    else:
        try:
            diagnosis_data = diagnose_investigation(investigation_data)
        except (LLMClientError, RootCauseAnalyzerError) as exc:
            logger.warning(f"AI diagnosis unavailable, returning fallback: {exc}")
            diagnosis_data = build_ai_unavailable_diagnosis(
                investigation_data,
                str(exc),
                build_deterministic_diagnosis=build_deterministic_diagnosis,
                generic_fallback_diagnosis=_fallback_diagnosis,
            )
            warnings.append(f"AI diagnosis unavailable: {exc}")
        except Exception as exc:
            logger.exception("AI diagnosis failed with unexpected error")
            diagnosis_data = build_ai_unavailable_diagnosis(
                investigation_data,
                f"Unexpected AI error: {exc}",
                build_deterministic_diagnosis=build_deterministic_diagnosis,
                generic_fallback_diagnosis=_fallback_diagnosis,
            )
            warnings.append(f"AI diagnosis failed: {exc}")

    diagnosis_data = finalize_diagnosis(diagnosis_data, investigation_data)

    report("ai_reasoning", "complete")
    report("root_cause_found", "complete")
    store.complete_investigation(investigation_data, diagnosis_data)

    ai_elapsed = time.perf_counter() - ai_start
    logger.info(f"AI diagnosis completed in {ai_elapsed:.2f}s")

    total_elapsed = time.perf_counter() - investigation_start
    logger.info(f"POST /investigate completed in {total_elapsed:.2f}s")

    payload = InvestigationPayload(
        pods=investigation_data["pods"],
        logs=investigation_data["logs"],
        events=investigation_data["events"],
        deployments=investigation_data["deployments"],
        network=investigation_data["network"],
    )

    return InvestigateResponse(
        status="success",
        investigation=payload,
        diagnosis=Diagnosis(**diagnosis_data),
        warnings=warnings,
        cluster_healthy=cluster_healthy,
        cluster_context=request.cluster_context,
    )
