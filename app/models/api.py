from typing import Literal

from pydantic import BaseModel, Field


RoastIntensity = Literal["mild", "medium", "brutal", "hell"]
ReviewStatusValue = Literal["pending", "approved", "rejected"]
ProjectType = Literal["web_app", "api_backend", "cli_tool", "data_science", "library", "other"]


class AuditRequest(BaseModel):
    username: str = Field(min_length=1, max_length=39, pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
    roast_intensity: RoastIntensity


class OptOutRequest(BaseModel):
    username: str = Field(min_length=1, max_length=39, pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")


class RejectReviewRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class RoadmapItem(BaseModel):
    week: int
    focus: str
    actions: list[str]


class RoastOutput(BaseModel):
    roast_text: str
    strengths: list[str] = Field(min_length=3, max_length=5)
    improvement_areas: list[str] = Field(min_length=3, max_length=5)
    roadmap: list[RoadmapItem]


class ProjectEvaluationRequest(BaseModel):
    repo_url: str = Field(min_length=12, max_length=300, pattern=r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$")
    problem_statement: str = Field(min_length=20, max_length=4000)


class ProjectEvidencePoint(BaseModel):
    file: str
    detail: str


class ProjectCategoryEvaluation(BaseModel):
    score: int = Field(ge=0, le=100)
    band_justification: str
    evidence: list[ProjectEvidencePoint] = Field(default_factory=list)


class ProjectEvaluationFlags(BaseModel):
    claims_exceed_evidence: bool = False
    possible_stub_implementation: bool = False
    insufficient_evidence_gathered: bool = False


class ProjectEvaluationResponse(BaseModel):
    project_type: ProjectType
    excluded_categories: list[str] = Field(default_factory=list)
    categories: dict[str, ProjectCategoryEvaluation]
    overall_score: float
    grade_label: str
    calibration_note: str
    flags: ProjectEvaluationFlags
