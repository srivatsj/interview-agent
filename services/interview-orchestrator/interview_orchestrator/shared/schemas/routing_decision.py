"""Routing decision schema for interview type and company"""

from pydantic import BaseModel, Field


class RoutingDecision(BaseModel):
    """Routing decision for interview type and company.

    NOTE: Validation is done dynamically via AgentProviderRegistry.is_valid_combination(),
    which checks both remote agents (configured in .env) and local fallback options.
    This allows for flexible company/type combinations without hardcoded Literal types.
    """

    company: str = Field(
        description="The company for the interview practice (validated via registry)"
    )
    interview_type: str = Field(
        description="The type of technical interview (validated via registry)"
    )
    confidence: float = Field(description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0)
