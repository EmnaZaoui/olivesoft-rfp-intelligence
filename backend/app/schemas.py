from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class TenderCreate(BaseModel):
    source: str
    raw_text: str


class TenderOut(BaseModel):
    id: str
    source: str
    source_url: Optional[str] = None
    title: Optional[str] = None
    issuing_organization: Optional[str] = None
    sector: Optional[str] = None
    estimated_budget: Optional[str] = None
    deadline: Optional[str] = None
    requirements: Optional[List[str]] = None
    summary: Optional[str] = None
    status: str

    technical_fit_score: Optional[float] = None
    budget_sufficient: Optional[bool] = None
    sector_strategic: Optional[bool] = None
    deadline_feasible: Optional[bool] = None
    is_expired: Optional[bool] = None
    urgent_deadline_alert: Optional[bool] = None
    qualification_score: Optional[float] = None
    qualification_reasons: Optional[List[str]] = None

    class Config:
        from_attributes = True


class DocumentIngest(BaseModel):
    title: str
    doc_type: str
    content: str


class RagSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class RagChunkResult(BaseModel):
    document_title: str
    doc_type: str
    content: str
    score: float


class ProspectOut(BaseModel):
    id: str
    tender_id: str
    company_name: Optional[str]
    sector: Optional[str]
    estimated_revenue: Optional[str]
    key_partners: Optional[List[str]]
    past_projects: Optional[List[str]]
    research_notes: Optional[str]

    class Config:
        from_attributes = True


class RequirementMatchOut(BaseModel):
    id: str
    tender_id: str
    requirement_text: str
    score: float
    covered: bool
    best_document_title: Optional[str] = None
    justification: Optional[str] = None
    concrete_evidence: Optional[str] = None

    class Config:
        from_attributes = True


class CompetitorInsightOut(BaseModel):
    id: str
    tender_id: str
    estimated_budget_range: Optional[str] = None
    confidence: Optional[str] = None
    competitive_positioning: Optional[str] = None
    likely_competitors: Optional[List[str]] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ProposalDraftOut(BaseModel):
    id: str
    tender_id: str
    content_markdown: str
    content_sections: Optional[Dict[str, Any]] = None
    status: str
    review_feedback: Optional[str] = None
    iterations: int

    class Config:
        from_attributes = True


class SectionEditRequest(BaseModel):
    instruction: str