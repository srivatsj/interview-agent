"""Candidate information schema"""

from pydantic import BaseModel, Field


class CandidateInfo(BaseModel):
    """Candidate background information collected during intro"""

    name: str = Field(description="Candidate's name")
    years_experience: int = Field(description="Years of professional experience", ge=0)
    domain: str = Field(
        description="Primary domain expertise (e.g., distributed systems, frontend)"
    )
    projects: str = Field(description="Notable projects the candidate has worked on")
