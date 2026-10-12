from datetime import datetime
import re
import dateparser
from sqlalchemy.orm import Session

from app.models import Tender, RequirementMatch
from app.business_rules import (
    QUALIFICATION_THRESHOLD, MIN_VIABLE_BUDGET_TND, URGENT_DEADLINE_DAYS,
    MIN_FEASIBLE_DEADLINE_DAYS, STRATEGIC_SECTORS,
)

BUDGET_NUMBER_REGEX = re.compile(r"(\d[\d\s.,]{2,})")


def _parse_budget_value(budget_text: str | None) -> float | None:
    if not budget_text or budget_text.lower() == "unknown":
        return None
    match = BUDGET_NUMBER_REGEX.search(budget_text.replace(" ", ""))
    if not match:
        return None
    raw = match.group(1).replace(" ", "").replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_deadline(deadline_text: str | None):
    if not deadline_text or deadline_text.lower() == "unknown":
        return None
    return dateparser.parse(deadline_text, languages=["fr", "en"])


def _rule_score(value: bool | None, true_score: float, unknown_score: float, false_score: float) -> float:
    if value is None:
        return unknown_score
    return true_score if value else false_score


def qualify_tender(db: Session, tender: Tender) -> Tender:
    flags: list[str] = []

    # --- 1. Fit technique (issu du matching exigence par exigence) ---
    matches = db.query(RequirementMatch).filter(RequirementMatch.tender_id == tender.id).all()
    technical_fit_score = sum(m.score for m in matches) / len(matches) if matches else 0.0
    if not matches:
        flags.append("Aucune exigence exploitable pour le matching technique.")

    # --- 2. Deadline (parsing réel + alertes) ---
    deadline_date = _parse_deadline(tender.deadline)
    is_expired = False
    deadline_feasible = None
    urgent_alert = False

    if deadline_date:
        tender.deadline_date = deadline_date
        days_remaining = (deadline_date - datetime.utcnow()).days
        if days_remaining < 0:
            is_expired = True
            flags.append("Deadline dépassée: ce tender est expiré.")
        else:
            deadline_feasible = days_remaining >= MIN_FEASIBLE_DEADLINE_DAYS
            if days_remaining <= URGENT_DEADLINE_DAYS:
                urgent_alert = True
                flags.append(f"ALERTE URGENCE: deadline dans {days_remaining} jour(s) seulement.")
            elif not deadline_feasible:
                flags.append(f"Deadline serrée: {days_remaining} jour(s) restants.")
    else:
        flags.append("Deadline non identifiable dans le texte source.")

    # --- 3. Budget ---
    budget_value = _parse_budget_value(tender.estimated_budget)
    budget_sufficient = budget_value >= MIN_VIABLE_BUDGET_TND if budget_value is not None else None
    if budget_value is None:
        flags.append("Budget non identifiable dans le texte source.")
    elif not budget_sufficient:
        flags.append(f"Budget estimé ({budget_value}) sous le seuil de rentabilité ({MIN_VIABLE_BUDGET_TND}).")

    # --- 4. Secteur stratégique ---
    sector_strategic = None
    if tender.sector and tender.sector.lower() != "unknown":
        sector_strategic = any(s in tender.sector.lower() for s in STRATEGIC_SECTORS)
    else:
        flags.append("Secteur non identifiable dans le texte source.")

    # --- 5. Score global pondéré ---
    qualification_score = (
        0.50 * technical_fit_score
        + 0.20 * _rule_score(budget_sufficient, 100, 50, 10)
        + 0.15 * _rule_score(sector_strategic, 100, 50, 25)
        + 0.15 * _rule_score(deadline_feasible, 100, 50, 10)
    )

    tender.technical_fit_score = round(technical_fit_score, 1)
    tender.budget_sufficient = budget_sufficient
    tender.sector_strategic = sector_strategic
    tender.deadline_feasible = deadline_feasible
    tender.is_expired = is_expired
    tender.urgent_deadline_alert = urgent_alert
    tender.qualification_score = round(qualification_score, 1)
    tender.qualification_reasons = flags
    tender.data_quality_flags = flags

    if is_expired:
        tender.status = "rejected_expired"
    elif qualification_score >= QUALIFICATION_THRESHOLD:
        tender.status = "qualified"
    else:
        tender.status = "rejected_low_score"

    db.commit()
    db.refresh(tender)
    return tender