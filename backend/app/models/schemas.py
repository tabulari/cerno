from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Severity(str, enum.Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    P5 = "P5"


class IncidentState(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    TRIAGING = "TRIAGING"
    TRIAGED = "TRIAGED"
    TICKETED = "TICKETED"
    NOTIFIED = "NOTIFIED"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


# --- Auth ---

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Incident Input ---

class IncidentCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    service: str = Field(max_length=100, default="unknown")
    reporter_severity: Optional[Severity] = None


class IncidentResponse(BaseModel):
    id: int
    title: str
    description: str
    service: str
    state: IncidentState
    reporter_severity: Optional[Severity]
    triage_severity: Optional[Severity]
    triage_summary: Optional[str]
    triage_runbook: Optional[str]
    confidence: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Agent Pipeline Models ---

class CodeAnalysisResult(BaseModel):
    relevant_files: list[str] = Field(default_factory=list)
    code_snippets: list[str] = Field(default_factory=list)
    module: Optional[str] = None
    summary: str = ""


class LogParseResult(BaseModel):
    error_types: list[str] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    stack_traces: list[str] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    summary: str = ""


class ReasoningStep(BaseModel):
    agent: str
    duration_ms: int
    tool_calls: list[dict] = Field(default_factory=list)
    finding: str


class TriageResult(BaseModel):
    severity: Severity
    summary: str
    runbook: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_steps: list[ReasoningStep] = Field(default_factory=list)
    code_analysis: Optional[CodeAnalysisResult] = None
    log_analysis: Optional[LogParseResult] = None
    needs_human_review: bool = False


# --- State Transition ---

class StateTransition(BaseModel):
    incident_id: int
    from_state: IncidentState
    to_state: IncidentState
    timestamp: datetime
    duration_ms: Optional[int] = None
    metadata: dict = Field(default_factory=dict)
