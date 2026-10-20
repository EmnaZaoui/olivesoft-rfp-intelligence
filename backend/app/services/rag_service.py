from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import Document, DocumentChunk
from app.services.ollama_client import embed_text
from app.services.pdf_loader import extract_text_from_pdf, guess_doc_type
from app.services.doc_metadata_extraction import extract_document_metadata

INTERNAL_DOCS_PATH = Path(__file__).resolve().parents[2] / "data" / "internal_docs"


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


def ingest_document(db: Session, title: str, doc_type: str, content: str) -> Document | None:
    if not content or content.startswith("PDF_EXTRACTION_ERROR"):
        return None

    metadata = extract_document_metadata(content)

    document = Document(title=title, doc_type=doc_type, content=content, structured_metadata=metadata)
    db.add(document)
    db.flush()

    chunks = chunk_text(content)
    if not chunks:
        db.rollback()
        return None

    for idx, chunk in enumerate(chunks):
        embedding = embed_text(chunk)
        db.add(DocumentChunk(
            document_id=document.id,
            chunk_index=idx,
            content=chunk,
            embedding=embedding,
        ))

    db.commit()
    db.refresh(document)
    return document


def ingest_pdfs_from_folder(db: Session) -> list[str]:
    ingested = []
    if not INTERNAL_DOCS_PATH.exists():
        return ingested

    for pdf_path in INTERNAL_DOCS_PATH.glob("*.pdf"):
        existing = db.query(Document).filter(Document.title == pdf_path.name).first()
        if existing:
            continue

        content = extract_text_from_pdf(pdf_path)
        doc_type = guess_doc_type(pdf_path.name)
        document = ingest_document(db, title=pdf_path.name, doc_type=doc_type, content=content)
        if document:
            ingested.append(document.title)
    return ingested


def search_similar_chunks(db: Session, query: str, top_k: int = 5):
    query_embedding = embed_text(query)

    stmt = (
        select(
            DocumentChunk.content,
            Document.title,
            Document.doc_type,
            DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .order_by("distance")
        .limit(top_k)
    )
    rows = db.execute(stmt).all()

    return [
        {
            "document_title": title,
            "doc_type": doc_type,
            "content": content,
            "score": round(float(1 - distance), 4),
        }
        for content, title, doc_type, distance in rows
    ]