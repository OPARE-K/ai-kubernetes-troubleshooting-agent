"""Legacy module — use ai.agent for diagnosis."""

from ai.agent import AIAgent, diagnose_investigation


def analyze_cluster_state(investigation: dict) -> dict:
    """Backward-compatible wrapper for AI diagnosis."""
    return diagnose_investigation(investigation)
