from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.business_rules import (
    QUALIFICATION_THRESHOLD, MIN_TECHNICAL_FIT, MIN_VIABLE_BUDGET_TND,
    MIN_COVERAGE_FOR_PROPOSAL, COVERAGE_THRESHOLD, MAX_CREW_ITERATIONS,
)
from app.database import get_db
from app.models import Tender, Document, ProposalDraft, User
from app.security import get_current_user
from app.services.ollama_client import chat_text

router = APIRouter(prefix="/assistant", tags=["assistant"])

OUT_OF_SCOPE = (
    "Je suis l'assistant de la plateforme OliveSoft RFP Intelligence. "
    "Je peux uniquement répondre aux questions sur cette plateforme et sur vos appels d'offres."
)

STATUS_LABELS = {
    "new": "nouveau", "extracted": "extrait", "qualified": "qualifié", "researched": "prospect analysé",
    "drafted": "proposition prête", "rejected_low_score": "rejeté (score insuffisant)",
    "rejected_expired": "rejeté (expiré)", "rejected_irrelevant": "rejeté (hors périmètre)",
    "extraction_failed": "extraction échouée",
}

PLATFORM_GUIDE = f"""
PLATEFORME: OliveSoft RFP Intelligence (projet IEEE CSTAM Challenge). Elle détecte des appels d'offres,
les qualifie face aux compétences d'OliveSoft et génère des propositions commerciales (PPTX et PDF).

PIPELINE: Détection, Extraction, Matching et scoring par exigence (RAG), Qualification, Recherche prospect
(agent ReAct via MCP), Budget et concurrence (agent), Rédaction (CrewAI: rédacteur et relecteur),
édition humaine, Export PPTX et PDF. Tout tourne en local (Ollama, PostgreSQL avec pgvector), orchestré par n8n.

SOURCES DE DÉTECTION: Banque mondiale (API ouverte, la plus fiable), Apify (recherche Google et crawler),
Serper avec Playwright, saisie manuelle.

QUALIFICATION: un tender n'est jamais transformé en prospect automatiquement.
Score = 50% fit technique, 20% budget, 15% secteur stratégique, 15% délai réalisable.
Seuil de qualification: {QUALIFICATION_THRESHOLD}/100. Rejet si le fit technique est inférieur à {MIN_TECHNICAL_FIT}/100,
si la date limite est dépassée, ou si le tender est hors périmètre IT. Budget minimal viable: {MIN_VIABLE_BUDGET_TND:.0f} TND.
Alerte d'urgence si la date limite est à 3 jours ou moins.

MATRICE D'EXIGENCES: chaque exigence est comparée aux CV et projets indexés puis notée de 0 à 100 par un juge LLM.
Une exigence est couverte si son score atteint {COVERAGE_THRESHOLD:.0f}. La génération de proposition est refusée si moins de
{int(MIN_COVERAGE_FOR_PROPOSAL * 100)}% des exigences sont couvertes, pour ne rien inventer.

PROPOSITION: le rédacteur et le relecteur itèrent au maximum {MAX_CREW_ITERATIONS} fois. Un contrôle automatique supprime tout
chiffre absent des données. Le commercial peut modifier une section à la main ou la réécrire avec l'IA.

PAGES: Tableau de bord (KPI, graphiques), Appels d'offres (liste, détection, reprise des tenders en attente),
Détail d'un tender (onglets Informations et matrice, Prospect et marché, Proposition, Téléchargements),
Base de connaissances (documents RAG, upload PDF, recherche test), Benchmark RAG (Recall et MRR), Orchestration (n8n).

REPRISE: si un tender s'arrête, ouvrir sa page et cliquer sur Continuer le pipeline, ou utiliser le bouton Reprendre les
tenders en attente sur la liste. Les étapes déjà faites ne sont pas refaites. Relancer n8n ne reprend pas les anciens tenders.
"""

SYSTEM_PROMPT = f"""Tu es l'assistant intégré à la plateforme OliveSoft RFP Intelligence.
Règles strictes:
1. Tu réponds uniquement avec le GUIDE et les DONNÉES EN DIRECT fournis ci-dessous.
2. Si la question ne concerne pas la plateforme ou les appels d'offres de l'utilisateur, réponds exactement: "{OUT_OF_SCOPE}"
3. N'invente jamais un chiffre, un tender ou une fonctionnalité. Si l'information manque, dis-le simplement.
4. Réponds en français, de façon claire et courte (6 phrases maximum), sans emoji.
"""


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatIn(BaseModel):
    message: str
    history: list[ChatTurn] = []


def _live_data(db: Session) -> str:
    tenders = db.query(Tender).filter(Tender.status != "archived").all()
    counts = Counter(t.status for t in tenders)
    lines = [
        f"Tenders au total: {len(tenders)}",
        "Répartition: " + (", ".join(f"{STATUS_LABELS.get(k, k)}: {v}" for k, v in counts.items()) or "aucun"),
        f"Documents indexés: {db.query(Document).count()}",
        f"Propositions générées: {db.query(ProposalDraft).count()}",
    ]
    best = sorted(
        [t for t in tenders if t.qualification_score is not None],
        key=lambda t: t.qualification_score, reverse=True,
    )[:5]
    if best:
        lines.append("Meilleurs tenders:")
        for t in best:
            lines.append(
                f"- {(t.title or 'Sans titre')[:90]} | {t.issuing_organization or 'organisation non précisée'} | "
                f"score {round(t.qualification_score)}/100 | statut {STATUS_LABELS.get(t.status, t.status)} | "
                f"date limite {t.deadline or 'non précisée'}"
            )
    return "\n".join(lines)


@router.post("/chat")
def chat(payload: ChatIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message vide")
    if len(message) > 800:
        raise HTTPException(status_code=400, detail="Message trop long")

    history = "\n".join(
        f"{'Utilisateur' if t.role == 'user' else 'Assistant'}: {t.content[:500]}"
        for t in payload.history[-6:]
    )
    user_prompt = (
        f"GUIDE DE LA PLATEFORME:\n{PLATFORM_GUIDE}\n\nDONNÉES EN DIRECT:\n{_live_data(db)}\n\n"
        f"CONVERSATION RÉCENTE:\n{history or '(début de conversation)'}\n\n"
        f"QUESTION DE L'UTILISATEUR: {message}"
    )
    try:
        answer = chat_text(SYSTEM_PROMPT, user_prompt).strip()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Modèle local indisponible: {e}")
    return {"answer": answer or OUT_OF_SCOPE}