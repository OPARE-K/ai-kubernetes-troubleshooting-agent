from typing import Any

from pydantic import BaseModel, Field


class InvestigateRequest(BaseModel):
    investigation_id: str | None = None
    user_id: str | None = None
    cluster_context: str | None = None


class InvestigationPayload(BaseModel):
    pods: dict[str, Any]
    logs: dict[str, Any]
    events: dict[str, Any]
    deployments: dict[str, Any]
    network: dict[str, Any]


class Diagnosis(BaseModel):
    root_cause: str
    explanation: str
    fix: str
    kubectl_command: str
    kubectl_commands: list[str] = Field(default_factory=list)
    prevention_recommendation: str = ""
    confidence: int = Field(ge=0, le=100)
    confidence_reasoning: str = ""


class InvestigateResponse(BaseModel):
    status: str
    investigation: InvestigationPayload
    diagnosis: Diagnosis
    warnings: list[str] = []
    cluster_healthy: bool | None = None
    cluster_context: str | None = None
