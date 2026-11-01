from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tender, ProposalDraft, Document, DocumentChunk, RagBenchmarkRun, User
from app.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

QUALIFIED_STATUSES = {"qualified", "researched", "drafted"}
REJECTED_STATUSES = {"rejected_low_score", "rejected_expired", "rejected_irrelevant", "extraction_failed"}
EXTRACTED_OR_BEYOND = QUALIFIED_STATUSES | {"extracted", "rejected_low_score", "rejected_expired"}


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tenders = db.query(Tender).filter(Tender.status != "archived").all()
    total = len(tenders)

    by_status = Counter(t.status for t in tenders)
    by_source = Counter(t.source for t in tenders)

    sectors = Counter()
    for t in tenders:
        s = (t.sector or "").strip()
        sectors[s if s and s.lower() != "unknown" else "Non précisé"] += 1
    top = sectors.most_common(6)
    other = sum(sectors.values()) - sum(c for _, c in top)
    by_sector = [{"sector": k, "count": v} for k, v in top]
    if other > 0:
        by_sector.append({"sector": "Autres", "count": other})

    scores = [t.qualification_score for t in tenders if t.qualification_score is not None]
    qualified = sum(1 for t in tenders if t.status in QUALIFIED_STATUSES)

    funnel = [
        {"stage": "detected", "count": total},
        {"stage": "extracted", "count": sum(1 for t in tenders if t.status in EXTRACTED_OR_BEYOND)},
        {"stage": "qualified", "count": qualified},
        {"stage": "researched", "count": sum(1 for t in tenders if t.status in {"researched", "drafted"})},
        {"stage": "drafted", "count": sum(1 for t in tenders if t.status == "drafted")},
    ]

    proposals = db.query(ProposalDraft).all()
    last_bench = db.query(RagBenchmarkRun).order_by(RagBenchmarkRun.run_at.desc()).first()

    recent = sorted(tenders, key=lambda t: t.created_at or 0, reverse=True)[:6]

    return {
        "totals": {
            "tenders": total,
            "qualified": qualified,
            "rejected": sum(1 for t in tenders if t.status in REJECTED_STATUSES),
            "proposals": len(proposals),
            "approved_proposals": sum(1 for p in proposals if p.status == "approved"),
            "documents": db.query(Document).count(),
            "chunks": db.query(DocumentChunk).count(),
            "avg_qualification_score": round(sum(scores) / len(scores), 1) if scores else None,
        },
        "by_status": [{"status": k, "count": v} for k, v in by_status.items()],
        "by_sector": by_sector,
        "by_source": [{"source": k, "count": v} for k, v in by_source.items()],
        "funnel": funnel,
        "benchmark": (
            {"recall_at_k": last_bench.recall_at_k, "mrr": last_bench.mrr,
             "run_at": last_bench.run_at.isoformat()} if last_bench else None
        ),
        "recent": [
            {"id": t.id, "title": t.title, "issuing_organization": t.issuing_organization,
             "status": t.status, "qualification_score": t.qualification_score, "deadline": t.deadline}
            for t in recent
        ],
    }