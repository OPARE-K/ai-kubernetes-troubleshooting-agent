from typing import Any


class ConfidenceEngine:
    """Score diagnosis confidence using correlated Kubernetes evidence."""

    def score(
        self,
        investigation: dict[str, Any],
        llm_confidence: int,
        llm_reasoning: str,
    ) -> dict[str, Any]:
        evidence_score, evidence_signals = self._score_evidence(investigation)
        blended = int((llm_confidence * 0.6) + (evidence_score * 0.4))
        confidence = max(0, min(100, blended))

        reasoning_parts = []
        if llm_reasoning:
            reasoning_parts.append(llm_reasoning)
        if evidence_signals:
            reasoning_parts.append(
                "Evidence signals: " + "; ".join(evidence_signals)
            )
        else:
            reasoning_parts.append(
                "Low evidence density — confidence reduced due to limited cluster signals."
            )

        return {
            "confidence": confidence,
            "confidence_reasoning": " ".join(reasoning_parts).strip(),
            "evidence_score": evidence_score,
        }

    def _score_evidence(self, investigation: dict[str, Any]) -> tuple[int, list[str]]:
        score = 0
        signals: list[str] = []

        pods = investigation.get("pods", {})
        problematic_pods = pods.get("problematic_pods", [])
        if problematic_pods:
            score += 25
            statuses = {pod.get("status") for pod in problematic_pods}
            signals.append(f"problematic pod states: {', '.join(sorted(statuses))}")

        logs = investigation.get("logs", {})
        highlighted_logs = [
            entry
            for entry in logs.get("collected", [])
            if entry.get("highlights")
        ]
        if highlighted_logs:
            score += 25
            signals.append(f"log errors found in {len(highlighted_logs)} pod(s)")

        events = investigation.get("events", {})
        findings = events.get("findings", [])
        if findings:
            score += 20
            reasons = {finding.get("reason") for finding in findings}
            signals.append(f"cluster events: {', '.join(sorted(reason for reason in reasons if reason))}")

        deployments = investigation.get("deployments", {})
        bad_deployments = deployments.get("problematic_deployments", [])
        if bad_deployments:
            score += 15
            signals.append(f"{len(bad_deployments)} unhealthy deployment(s)")

        network = investigation.get("network", {})
        network_findings = network.get("findings", [])
        if network_findings:
            score += 15
            signals.append(f"{len(network_findings)} networking finding(s)")

        if any(
            isinstance(section, dict) and section.get("error")
            for section in investigation.values()
        ):
            score = min(score, 30)
            signals.append("kubectl collection errors reduced evidence quality")

        return min(score, 100), signals
