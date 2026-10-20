import json
from pathlib import Path
from sqlalchemy.orm import Session

from app.models import RagBenchmarkRun
from app.services.rag_service import search_similar_chunks

TEST_SET_PATH = Path(__file__).resolve().parents[2] / "data" / "rag_benchmark" / "test_set.json"


def _load_test_set() -> list[dict]:
    if not TEST_SET_PATH.exists():
        return []
    with open(TEST_SET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_benchmark(db: Session, top_k: int = 5) -> dict:
    test_set = _load_test_set()
    if not test_set:
        return {"error": "Aucun jeu de test trouvé. Créez backend/data/rag_benchmark/test_set.json"}

    recall_scores, reciprocal_ranks, details = [], [], []

    for case in test_set:
        query = case["query"]
        expected_titles = set(case["relevant_document_titles"])
        results = search_similar_chunks(db, query, top_k=top_k)
        retrieved_titles = [r["document_title"] for r in results]

        hit_titles = {t for t in retrieved_titles if t in expected_titles}
        recall = len(hit_titles) / len(expected_titles) if expected_titles else 0.0
        recall_scores.append(recall)

        rr = 0.0
        for rank, title in enumerate(retrieved_titles, start=1):
            if title in expected_titles:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

        details.append({
            "query": query, "expected": list(expected_titles),
            "retrieved": retrieved_titles, "recall": round(recall, 3), "reciprocal_rank": round(rr, 3),
        })

    recall_at_k = round(sum(recall_scores) / len(recall_scores), 3) if recall_scores else 0.0
    mrr = round(sum(reciprocal_ranks) / len(reciprocal_ranks), 3) if reciprocal_ranks else 0.0

    run = RagBenchmarkRun(recall_at_k=recall_at_k, mrr=mrr, details=details)
    db.add(run)
    db.commit()
    db.refresh(run)

    return {"run_id": run.id, "recall_at_k": recall_at_k, "mrr": mrr, "top_k": top_k, "details": details}