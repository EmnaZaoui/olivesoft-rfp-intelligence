from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, DocumentChunk, RagBenchmarkRun, User
from app.security import get_current_user
from app.services.pdf_loader import extract_text_from_pdf, guess_doc_type
from app.services.rag_service import ingest_document, INTERNAL_DOCS_PATH

router = APIRouter(prefix="/rag", tags=["knowledge base"])

VALID_TYPES = {"cv", "project", "reference"}


@router.get("/documents")
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    chunk_counts = dict(
        db.query(DocumentChunk.document_id, func.count(DocumentChunk.id))
        .group_by(DocumentChunk.document_id).all()
    )
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id, "title": d.title, "doc_type": d.doc_type,
            "chunks": chunk_counts.get(d.id, 0),
            "metadata": d.structured_metadata or {},
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("auto"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    name = Path(file.filename or "").name
    if not name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")
    if db.query(Document).filter(Document.title == name).first():
        raise HTTPException(status_code=409, detail="Un document portant ce nom est déjà indexé")

    INTERNAL_DOCS_PATH.mkdir(parents=True, exist_ok=True)
    target = INTERNAL_DOCS_PATH / name
    target.write_bytes(file.file.read())

    resolved_type = doc_type if doc_type in VALID_TYPES else guess_doc_type(name)
    content = extract_text_from_pdf(target)
    document = ingest_document(db, title=name, doc_type=resolved_type, content=content)
    if not document:
        target.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail="PDF illisible ou sans texte (document scanné ?). Aucun contenu n'a pu être indexé.",
        )
    return {"id": document.id, "title": document.title, "doc_type": document.doc_type, "status": "indexed"}


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document introuvable")
    title = document.title
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()
    db.delete(document)
    db.commit()
    (INTERNAL_DOCS_PATH / title).unlink(missing_ok=True)
    return {"status": "deleted", "title": title}


@router.get("/benchmark/history")
def benchmark_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    runs = db.query(RagBenchmarkRun).order_by(RagBenchmarkRun.run_at.desc()).limit(20).all()
    return [
        {
            "id": r.id, "run_at": r.run_at.isoformat() if r.run_at else None,
            "recall_at_k": r.recall_at_k, "mrr": r.mrr,
            "queries": len(r.details or []), "details": r.details or [],
        }
        for r in runs
    ]