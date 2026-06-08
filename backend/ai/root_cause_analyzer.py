import json
import re
from typing import Any

from loguru import logger


class RootCauseAnalyzerError(Exception):
    """Raised when the LLM response cannot be parsed into a diagnosis."""


class RootCauseAnalyzer:
    """Parse and validate LLM reasoning into a structured root cause analysis."""

    def analyze(self, llm_response: str, investigation: dict[str, Any]) -> dict[str, Any]:
        parsed = self._parse_response(llm_response)
        self._validate_fields(parsed)

        root_cause = parsed["root_cause"].strip()
        explanation = parsed["explanation"].strip()

        if self._evidence_is_sparse(investigation):
            explanation = (
                f"{explanation} Note: Limited cluster evidence was available, "
                "so this diagnosis should be validated against live cluster state."
            )

        return {
            "root_cause": root_cause,
            "explanation": explanation,
            "raw_llm_confidence": self._parse_confidence(parsed.get("confidence")),
            "confidence_reasoning": parsed.get("confidence_reasoning", "").strip(),
            "prevention_recommendation": parsed.get("prevention_recommendation", "").strip(),
            "_parsed": parsed,
        }

    def _parse_response(self, llm_response: str) -> dict[str, Any]:
        cleaned = llm_response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON response")
            raise RootCauseAnalyzerError("LLM returned invalid JSON") from exc

        if not isinstance(data, dict):
            raise RootCauseAnalyzerError("LLM response must be a JSON object")

        return data

    def _validate_fields(self, parsed: dict[str, Any]) -> None:
        required = ["root_cause", "explanation", "fix", "kubectl_command"]
        missing = [field for field in required if not str(parsed.get(field, "")).strip()]
        if missing:
            raise RootCauseAnalyzerError(
                f"LLM response missing required fields: {', '.join(missing)}"
            )

    def _parse_confidence(self, value: Any) -> int:
        try:
            confidence = int(value)
        except (TypeError, ValueError):
            return 50
        return max(0, min(100, confidence))

    def _evidence_is_sparse(self, investigation: dict[str, Any]) -> bool:
        pods = investigation.get("pods", {})
        logs = investigation.get("logs", {})
        events = investigation.get("events", {})

        has_pod_issues = bool(pods.get("problematic_pods"))
        has_log_highlights = any(
            entry.get("highlights") for entry in logs.get("collected", [])
        )
        has_events = bool(events.get("findings"))
        has_errors = any(
            section.get("error")
            for section in investigation.values()
            if isinstance(section, dict)
        )

        if has_errors and not (has_pod_issues or has_log_highlights or has_events):
            return True

        return not (has_pod_issues or has_log_highlights or has_events)
