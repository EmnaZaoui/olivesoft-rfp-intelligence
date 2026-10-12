from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DocumentIngest, RagSearchRequest, RagChunkResult
from app.services.rag_service import ingest_document, ingest_pdfs_from_folder, search_similar_chunks
from app.services.rag_benchmark_service import run_benchmark

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ingest")
def ingest(payload: DocumentIngest, db: Session = Depends(get_db)):
    doc = ingest_document(db, payload.title, payload.doc_type, payload.content)
    if not doc:
        return {"status": "failed", "reason": "contenu vide ou illisible"}
    return {"id": doc.id, "title": doc.title, "status": "ingested"}


@router.post("/ingest/bootstrap")
def bootstrap_internal_docs(db: Session = Depends(get_db)):
    ingested = ingest_pdfs_from_folder(db)
    return {"ingested_documents": ingested, "count": len(ingested)}


@router.post("/search", response_model=list[RagChunkResult])
def search(payload: RagSearchRequest, db: Session = Depends(get_db)):
    return search_similar_chunks(db, payload.query, payload.top_k)


@router.post("/benchmark/run")
def benchmark(top_k: int = 5, db: Session = Depends(get_db)):
    return run_benchmark(db, top_k=top_k)