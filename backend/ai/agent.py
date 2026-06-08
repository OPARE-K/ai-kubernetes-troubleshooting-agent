from typing import Any

from ai.confidence_engine import ConfidenceEngine
from services.finding_prioritizer import (
    build_deterministic_diagnosis,
    mentions_primary_issue,
)
from ai.fix_recommendation import FixRecommendationEngine
from ai.llm_client import LLMClient, LLMClientError
from ai.prompt_builder import PromptBuilder
from ai.root_cause_analyzer import RootCauseAnalyzer, RootCauseAnalyzerError
from loguru import logger


class AIAgent:
    """Senior Kubernetes SRE agent — reasons over investigation evidence."""

    def __init__(self) -> None:
        self.prompt_builder = PromptBuilder()
        self.llm_client = LLMClient()
        self.root_cause_analyzer = RootCauseAnalyzer()
        self.fix_engine = FixRecommendationEngine()
        self.confidence_engine = ConfidenceEngine()

    def diagnose(self, investigation: dict[str, Any]) -> dict[str, Any]:
        logger.info("Starting AI diagnosis")

        messages = self.prompt_builder.build_messages(investigation)
        llm_response = self.llm_client.complete(messages)

        root_cause_result = self.root_cause_analyzer.analyze(llm_response, investigation)
        parsed = root_cause_result.pop("_parsed")

        priority = investigation.get("priority_analysis", {})
        recommended = priority.get("recommended_primary_issue")
        user_findings = priority.get("primary_user_findings", [])
        if (
            user_findings
            and recommended
            and not mentions_primary_issue(root_cause_result["root_cause"], recommended)
        ):
            deterministic = build_deterministic_diagnosis(investigation)
            if deterministic:
                logger.warning(
                    "LLM root cause did not mention primary user workload; "
                    "using workload-first diagnosis for {}/{}",
                    recommended.get("namespace"),
                    recommended.get("name"),
                )
                root_cause_result["root_cause"] = deterministic["root_cause"]
                root_cause_result["explanation"] = deterministic["explanation"]
                parsed["fix"] = deterministic["fix"]
                parsed["kubectl_command"] = deterministic["kubectl_command"]
                parsed["prevention_recommendation"] = deterministic[
                    "prevention_recommendation"
                ]
                root_cause_result["raw_llm_confidence"] = deterministic["confidence"]
                root_cause_result["confidence_reasoning"] = deterministic[
                    "confidence_reasoning"
                ]

        fix_result = self.fix_engine.build(parsed, investigation)
        confidence_result = self.confidence_engine.score(
            investigation=investigation,
            llm_confidence=root_cause_result["raw_llm_confidence"],
            llm_reasoning=root_cause_result.get("confidence_reasoning", ""),
        )

        diagnosis = {
            "root_cause": root_cause_result["root_cause"],
            "explanation": root_cause_result["explanation"],
            "fix": fix_result["fix"],
            "kubectl_command": fix_result["kubectl_command"],
            "kubectl_commands": fix_result.get("kubectl_commands", []),
            "prevention_recommendation": fix_result["prevention_recommendation"],
            "confidence": confidence_result["confidence"],
            "confidence_reasoning": confidence_result["confidence_reasoning"],
        }

        logger.info(
            f"AI diagnosis complete — confidence {diagnosis['confidence']}%"
        )
        return diagnosis


def diagnose_investigation(investigation: dict[str, Any]) -> dict[str, Any]:
    """Convenience entry point for the AI agent."""
    return AIAgent().diagnose(investigation)


# Re-export errors for API layer
__all__ = [
    "AIAgent",
    "diagnose_investigation",
    "LLMClientError",
    "RootCauseAnalyzerError",
]
