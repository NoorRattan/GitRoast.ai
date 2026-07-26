from typing import Literal

from pydantic import BaseModel, Field


RoastIntensity = Literal["mild", "medium", "brutal", "hell"]
ReviewStatusValue = Literal["pending", "approved", "rejected"]


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
