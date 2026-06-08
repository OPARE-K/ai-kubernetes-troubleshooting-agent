from typing import Any

from core.config import settings
from kubernetes.deployment_inspector import DeploymentInspector
from kubernetes.events_analyzer import EventsAnalyzer
from kubernetes.executor import KubectlExecutor
from kubernetes.logs_collector import LogsCollector
from kubernetes.network_inspector import NetworkInspector
from kubernetes.pod_inspector import PodInspector
from loguru import logger
from services.finding_prioritizer import enrich_investigation_priorities
from services.progress_reporter import ProgressCallback


class InvestigationService:
    """Orchestrate Kubernetes evidence collection across all inspectors."""

    def __init__(
        self,
        kubeconfig_path: str | None = None,
        cluster_context: str | None = None,
    ) -> None:
        path = kubeconfig_path if kubeconfig_path is not None else settings.kubeconfig_path
        self.cluster_context = cluster_context or ""
        self.executor = KubectlExecutor(
            kubeconfig_path=path,
            context=self.cluster_context,
        )
        self.pod_inspector = PodInspector(self.executor)
        self.logs_collector = LogsCollector(self.executor)
        self.events_analyzer = EventsAnalyzer(self.executor)
        self.deployment_inspector = DeploymentInspector(self.executor)
        self.network_inspector = NetworkInspector(self.executor)

    def check_connectivity(self) -> tuple[bool, str]:
        result = self.executor.run("get", "nodes", "--request-timeout=8s", timeout=12)
        if result.success:
            return True, ""
        from services.k8s_errors import friendly_kubectl_error

        return False, friendly_kubectl_error(
            result,
            context=self.cluster_context or None,
        )

    def run_investigation(
        self, on_progress: ProgressCallback | None = None
    ) -> dict[str, Any]:
        report = on_progress or (lambda _step, _status="complete": None)

        logger.info("Starting Kubernetes investigation")
        report("checking_pods", "running")

        pods = self.pod_inspector.inspect()
        report("checking_pods", "complete")
        total_pods = pods.get("total_pods", 0)
        problematic = pods.get("problematic_pods", [])
        logger.info(
            f"Pod inspection complete — scanned {total_pods} pod(s), "
            f"found {len(problematic)} problematic pod(s)"
        )

        report("reading_logs", "running")
        logs = self.logs_collector.collect(pods.get("problematic_pods", []))
        report("reading_logs", "complete")
        logger.info("Log collection complete")

        report("analyzing_events", "running")
        events = self.events_analyzer.analyze()
        report("analyzing_events", "complete")
        logger.info(
            f"Events analysis complete — {len(events.get('findings', []))} finding(s)"
        )

        report("inspecting_deployments", "running")
        deployments = self.deployment_inspector.inspect()
        report("inspecting_deployments", "complete")
        logger.info(
            f"Deployment inspection complete — "
            f"{len(deployments.get('problematic_deployments', []))} problematic deployment(s)"
        )

        report("checking_networking", "running")
        network = self.network_inspector.inspect()
        report("checking_networking", "complete")
        logger.info(
            f"Network inspection complete — {len(network.get('findings', []))} finding(s)"
        )

        investigation = {
            "cluster_context": self.cluster_context or None,
            "pods": pods,
            "logs": logs,
            "events": events,
            "deployments": deployments,
            "network": network,
        }
        enrich_investigation_priorities(investigation)

        logger.info("Kubernetes investigation finished")
        return investigation
