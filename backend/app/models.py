import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, JSON
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
    sector = Column(String, nullable=True)
    issuing_organization = Column(String, nullable=True)  
    estimated_budget = Column(String, nullable=True)
    deadline = Column(String, nullable=True)
    requirements = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    status = Column(String, default="new")               
    created_at = Column(DateTime, default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False, unique=True)  
    doc_type = Column(String, nullable=False)             
    content = Column(Text, nullable=False)
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


class ProposalDraft(Base):
    __tablename__ = "proposal_drafts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    tender_id = Column(UUID(as_uuid=False), ForeignKey("tenders.id"), nullable=False)
    content_markdown = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)