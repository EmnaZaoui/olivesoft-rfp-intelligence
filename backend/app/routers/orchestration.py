from datetime import datetime

import requests
from fastapi import APIRouter, Depends

from app.config import settings
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/orchestration", tags=["orchestration"])


def _parse(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@router.get("/executions")
def executions(limit: int = 20, user: User = Depends(get_current_user)):
    base = settings.n8n_base_url.rstrip("/")
    if not settings.n8n_api_key:
        return {"configured": False, "base_url": base, "executions": [],
                "message": "Ajoutez N8N_API_KEY dans backend/.env pour afficher les exécutions."}
    try:
        response = requests.get(
            f"{base}/api/v1/executions",
            headers={"X-N8N-API-KEY": settings.n8n_api_key},
            params={"limit": limit}, timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        return {"configured": True, "base_url": base, "executions": [], "error": f"n8n injoignable: {e}"}

    items = []
    for e in response.json().get("data", []):
        started, stopped = _parse(e.get("startedAt")), _parse(e.get("stoppedAt"))
        duration = round((stopped - started).total_seconds()) if started and stopped else None
        items.append({
            "id": e.get("id"),
            "status": e.get("status") or ("success" if e.get("finished") else "error"),
            "mode": e.get("mode"),
            "started_at": e.get("startedAt"),
            "duration_seconds": duration,
            "workflow_id": e.get("workflowId"),
        })
    return {"configured": True, "base_url": base, "executions": items}