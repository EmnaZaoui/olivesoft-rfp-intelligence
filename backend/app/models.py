import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, JSON, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.config import settings


def gen_uuid():
    return str(uuid.uuid4())


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    source = Column(String, nullable=False)
    source_url = Column(String, unique=True, nullable=True)
    raw_text = Column(Text, nullable=False)
    title = Column(String, nullable=True)
    issuing_organization = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    estimated_budget = Column(String, nullable=True)
    deadline = Column(String, nullable=True)
    requirements = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    status = Column(String, default="new")

    # --- Qualification (Phase 2) ---
    deadline_date = Column(DateTime, nullable=True)
    is_expired = Column(Boolean, default=False)
    technical_fit_score = Column(Float, nullable=True)
    budget_sufficient = Column(Boolean, nullable=True)
    sector_strategic = Column(Boolean, nullable=True)
    deadline_feasible = Column(Boolean, nullable=True)
    urgent_deadline_alert = Column(Boolean, default=False)
    qualification_score = Column(Float, nullable=True)
    qualification_reasons = Column(JSON, nullable=True)
    data_quality_flags = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False, unique=True)
    doc_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    structured_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    document_id = Column(UUID(as_uuid=False), ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(settings.embedding_dim), nullable=False)


class Prospect(Base):
    __tablename__ = "prospects"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tender_id = Column(UUID(as_uuid=False), ForeignKey("tenders.id"), nullable=False)
    company_name = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    estimated_revenue = Column(String, nullable=True)
    key_partners = Column(JSON, nullable=True)
    past_projects = Column(JSON, nullable=True)
    research_notes = Column(Text, nullable=True)
    raw_agent_trace = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RequirementMatch(Base):
    __tablename__ = "requirement_matches"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tender_id = Column(UUID(as_uuid=False), ForeignKey("tenders.id"), nullable=False)
    requirement_text = Column(Text, nullable=False)
    score = Column(Float, nullable=False)
    covered = Column(Boolean, nullable=False)
    best_document_title = Column(String, nullable=True)
    justification = Column(Text, nullable=True)
    concrete_evidence = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CompetitorInsight(Base):
    __tablename__ = "competitor_insights"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tender_id = Column(UUID(as_uuid=False), ForeignKey("tenders.id"), nullable=False)
    estimated_budget_range = Column(String, nullable=True)
    confidence = Column(String, nullable=True)
    competitive_positioning = Column(Text, nullable=True)
    likely_competitors = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    raw_trace = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProposalDraft(Base):
    __tablename__ = "proposal_drafts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tender_id = Column(UUID(as_uuid=False), ForeignKey("tenders.id"), nullable=False)
    content_markdown = Column(Text, nullable=False)
    content_sections = Column(JSON, nullable=True)
    status = Column(String, default="draft")   # draft | needs_review | approved
    review_feedback = Column(Text, nullable=True)
    iterations = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class RagBenchmarkRun(Base):
    __tablename__ = "rag_benchmark_runs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    run_at = Column(DateTime, default=datetime.utcnow)
    recall_at_k = Column(Float, nullable=True)
    mrr = Column(Float, nullable=True)
    details = Column(JSON, nullable=True)