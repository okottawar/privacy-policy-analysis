"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import Optional


class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="Public URL of the privacy policy to analyze")
    policy_text: Optional[str] = Field(
        None, description="Optional: paste policy text directly instead of fetching by URL"
    )


class EvidenceChunk(BaseModel):
    content: str
    section: str
    similarity_score: float


class RiskFinding(BaseModel):
    risk_category: str
    risk_score: int = Field(..., ge=0, le=10)
    summary: str
    key_findings: list[str]
    evidence: list[str]
    red_flags: list[str]
    positive_indicators: list[str]
    evidence_chunks: list[EvidenceChunk]
    score_method: str


class OverallScore(BaseModel):
    score: float
    label: str
    color: str


class AnalyzeResponse(BaseModel):
    url: str
    overall: OverallScore
    findings: list[RiskFinding]
    total_chunks: int
    total_sections: int
    executive_summary: str
