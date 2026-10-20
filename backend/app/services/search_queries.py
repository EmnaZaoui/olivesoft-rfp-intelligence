import random
from collections import Counter
from datetime import date

from sqlalchemy.orm import Session

from app.models import Document

IT_TOPICS_FR = [
    "développement application web", "développement application mobile",
    "plateforme digitale", "système d'information", "refonte site web portail",
    "digitalisation des processus", "gestion électronique des documents",
    "ERP gestion intégrée", "développement logiciel sur mesure",
    "intelligence artificielle", "tableau de bord business intelligence",
    "maintenance applicative", "application e-commerce", "assistance technique développeurs",
]

IT_TOPICS_EN = [
    "software development services", "web application development",
    "digital transformation platform", "mobile application development",
    "information system development",
]

# Portails ciblés via l'opérateur site: (complétez avec les portails que vous validez)
PORTAL_DOMAINS = ["j360.info", "appeloffres.com"]


def _top_technologies(db: Session, limit: int = 3) -> list[str]:
    """Technologies réellement présentes dans vos CV/projets -> requêtes alignées sur vos compétences."""
    counter: Counter = Counter()
    for (meta,) in db.query(Document.structured_metadata).all():
        if not meta:
            continue
        for tech in meta.get("technologies") or []:
            if isinstance(tech, str) and tech.strip() and tech.strip().lower() != "unknown":
                counter[tech.strip()] += 1
    return [t for t, _ in counter.most_common(limit)]


def build_queries(db: Session, max_queries: int = 12) -> list[str]:
    # Rotation quotidienne des sujets: deux lancements à des jours différents explorent des zones différentes
    rng = random.Random(date.today().toordinal())
    fr = IT_TOPICS_FR[:]
    en = IT_TOPICS_EN[:]
    rng.shuffle(fr)
    rng.shuffle(en)

    queries = []
    for topic in fr[:5]:
        queries.append('"appel d\'offres" {} Tunisie cahier des charges'.format(topic))
    for tech in _top_technologies(db):
        queries.append('"appel d\'offres" développement {} Tunisie date limite'.format(tech))
    for topic in en[:2]:
        queries.append('RFP OR tender "{}" Tunisia deadline'.format(topic))
    for domain in PORTAL_DOMAINS:
        queries.append('site:{} {} appel d\'offres'.format(domain, fr[0]))
    queries.append('"consultation" "développement" application Tunisie dépôt des offres')

    unique = list(dict.fromkeys(queries))
    return unique[:max_queries]