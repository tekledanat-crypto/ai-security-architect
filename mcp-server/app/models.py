"""Domain models shared across the MCP server.

These mirror the JSON Schemas in frameworks/schemas/ but as typed Python objects
so the tools and scoring engine have a stable, validated contract to work with.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low", "informational"]
Stride = Literal[
    "spoofing", "tampering", "repudiation",
    "information-disclosure", "denial-of-service", "elevation-of-privilege",
]


# ─────────────────────────── Framework data ───────────────────────────

class CheckHint(BaseModel):
    target: str
    property: Optional[str] = None
    condition: str
    value: Any = None
    fail_message: Optional[str] = None


class CrosswalkRef(BaseModel):
    framework_id: str
    control_id: str


class Control(BaseModel):
    control_id: str
    title: str
    summary: str
    severity: Severity
    domain: Optional[str] = None
    azure_services: list[str] = Field(default_factory=list)
    check_hints: list[CheckHint] = Field(default_factory=list)
    remediation: str
    stride: list[Stride] = Field(default_factory=list)
    attack_techniques: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    crosswalk: list[CrosswalkRef] = Field(default_factory=list)
    # populated at load time so a control always knows its parent framework:
    framework_id: str = ""
    framework_name: str = ""


class Framework(BaseModel):
    framework_id: str
    name: str
    version: str
    publisher: Optional[str] = None
    category: str
    description: Optional[str] = None
    reference_url: Optional[str] = None
    controls: list[Control]


# ─────────────────────────── Architecture ───────────────────────────

class ArchNode(BaseModel):
    id: str
    service: str
    label: Optional[str] = None
    zone: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)
    position: Optional[dict[str, float]] = None


class ArchEdge(BaseModel):
    id: Optional[str] = None
    source: str
    target: str
    label: Optional[str] = None
    protocol: Optional[str] = None
    private: Optional[bool] = None


class ArchContext(BaseModel):
    internet_facing: Optional[bool] = None
    stores_customer_data: Optional[bool] = None
    data_classification: Optional[str] = None
    regulatory: list[str] = Field(default_factory=list)
    environments: list[str] = Field(default_factory=list)
    third_party_access: Optional[bool] = None
    uses_ai_workloads: Optional[bool] = None


class Architecture(BaseModel):
    name: str
    description: Optional[str] = None
    context: ArchContext = Field(default_factory=ArchContext)
    nodes: list[ArchNode] = Field(default_factory=list)
    edges: list[ArchEdge] = Field(default_factory=list)

    def services(self) -> set[str]:
        return {n.service for n in self.nodes}

    def nodes_for(self, service: str) -> list[ArchNode]:
        return [n for n in self.nodes if n.service == service]


# ─────────────────────────── Results ───────────────────────────

class Finding(BaseModel):
    framework_id: str
    control_id: str
    title: str
    severity: Severity
    status: Literal["pass", "fail", "not-applicable"]
    message: str
    remediation: Optional[str] = None
    affected_nodes: list[str] = Field(default_factory=list)
    stride: list[Stride] = Field(default_factory=list)
    attack_techniques: list[str] = Field(default_factory=list)


class FrameworkScore(BaseModel):
    framework_id: str
    name: str
    status: Literal["PASS", "FAIL", "NOT-ASSESSED"]
    score: int  # 0-100
    passed: int
    failed: int
    applicable: int
    failed_controls: list[Finding] = Field(default_factory=list)


class AssessmentResult(BaseModel):
    architecture_name: str
    overall_score: int
    grade: str
    frameworks: list[FrameworkScore]
    findings: list[Finding]
    summary: dict[str, int]
