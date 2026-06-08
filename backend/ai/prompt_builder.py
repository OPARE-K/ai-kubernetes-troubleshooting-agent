import json
from typing import Any

SYSTEM_PROMPT = """You are a Senior Kubernetes SRE investigating a production incident.

Your job is to analyze collected cluster evidence, correlate signals across pods, logs, events, deployments, and networking, then produce a precise diagnosis.

Prioritization rules (IMPORTANT):
- User application/workload failures are ALWAYS more important than kube-system noise.
- Namespaces considered system/infrastructure: kube-system, kube-public, kube-node-lease, local-path-storage.
- All other namespaces are user workloads.
- If a user workload pod is Failed, Error, CrashLoopBackOff, ImagePullBackOff, or exited non-zero, that is the PRIMARY root cause.
- Do NOT choose kube-proxy, CoreDNS, or local-path-provisioner high restart counts as the root cause when a user workload is clearly failing.
- System pod issues may appear in the explanation as SECONDARY findings only.
- Missing logs do not mean a pod failure is unrelated — trust pod phase, container state, and termination reason.

General rules:
- Correlate evidence across all sections. Do not summarize a single log line in isolation.
- Be specific and actionable. Name resources (pods, deployments, services, namespaces).
- Suggest practical kubectl commands a beginner can run.
- Avoid vague advice like "check the logs" or "restart the pod" without context.
- If evidence is insufficient, state that clearly and lower confidence.

You MUST respond with valid JSON only (no markdown fences) using this exact schema:
{
  "root_cause": "One-sentence root cause",
  "explanation": "2-4 sentences correlating pod status, logs, events, deployments, and network findings. Mention secondary system issues separately if present.",
  "fix": "Clear actionable fix steps",
  "kubectl_command": "Primary kubectl command to apply the fix",
  "prevention_recommendation": "How to prevent recurrence",
  "confidence": 0,
  "confidence_reasoning": "Why this confidence score is justified based on evidence strength"
}

confidence must be an integer from 0 to 100."""


class PromptBuilder:
    """Build structured prompts from Kubernetes investigation evidence."""

    def build_messages(self, investigation: dict[str, Any]) -> list[dict[str, str]]:
        user_prompt = self._build_user_prompt(investigation)
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def _build_user_prompt(self, investigation: dict[str, Any]) -> str:
        pods = investigation.get("pods", {})
        logs = investigation.get("logs", {})
        events = investigation.get("events", {})
        deployments = investigation.get("deployments", {})
        network = investigation.get("network", {})
        priority = investigation.get("priority_analysis", {})

        problematic = pods.get("problematic_pods", [])
        pod_summary = (
            f"{len(problematic)} problematic pod(s) detected."
            if problematic
            else "No problematic pods detected."
        )

        return f"""Analyze this Kubernetes troubleshooting evidence and return your diagnosis as JSON.

## Prioritization (read this first)
{self._format_section(priority)}

## Pod Status Summary
{pod_summary}

## Pod Status
{self._format_section(pods)}

## Logs
{self._format_section(logs)}

## Events
{self._format_section(events)}

## Deployment Health
{self._format_section(deployments)}

## Networking Findings
{self._format_section(network)}

Use the prioritization section above. If a primary user workload failure is listed, that MUST be your root_cause. List system issues only as secondary context in the explanation."""

    def _format_section(self, data: Any) -> str:
        if not data:
            return "No data collected."
        return json.dumps(data, indent=2, default=str)
