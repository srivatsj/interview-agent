"""Routing decision schema for interview type and company"""

from typing import Literal

from pydantic import BaseModel, Field


class RoutingDecision(BaseModel):
    """Routing decision for interview type and company"""

    company: Literal["amazon", "google", "apple"] = Field(
        description="The company for the interview practice"
    )
    interview_type: Literal["system_design", "coding", "behavioral"] = Field(
        description="The type of technical interview"
    )
    confidence: float = Field(description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0)
