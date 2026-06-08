"""Legacy module — use dedicated inspector modules instead."""

from kubernetes.pod_inspector import PodInspector
from kubernetes.events_analyzer import EventsAnalyzer


def inspect_pods(executor=None) -> dict:
    """Backward-compatible wrapper for pod inspection."""
    from kubernetes.executor import KubectlExecutor

    inspector = PodInspector(executor or KubectlExecutor())
    return inspector.inspect()


def inspect_events(executor=None) -> dict:
    """Backward-compatible wrapper for event analysis."""
    from kubernetes.executor import KubectlExecutor

    analyzer = EventsAnalyzer(executor or KubectlExecutor())
    return analyzer.analyze()
