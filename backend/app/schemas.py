from typing import Optional, List
from pydantic import BaseModel


class TenderCreate(BaseModel):
    source: str
    raw_text: str


class TenderOut(BaseModel):
    id: str
    source: str
    source_url: Optional[str] = None
    title: Optional[str] = None
    sector: Optional[str] = None
    estimated_budget: Optional[str] = None
    deadline: Optional[str] = None
    requirements: Optional[List[str]] = None
    summary: Optional[str] = None
    status: str
    issuing_organization: Optional[str] = None
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