"""
Règles métier de qualification des tenders. Centralisées ici pour pouvoir
être ajustées facilement sans toucher à la logique des services.
"""

# Seuil minimal de couverture pour qu'une exigence individuelle soit "couverte"
COVERAGE_THRESHOLD = 50.0

# Score global minimal pour qu'un tender passe en statut "qualified"
QUALIFICATION_THRESHOLD = 55.0

# Budget plancher en dessous duquel un tender est jugé peu rentable (TND)
MIN_VIABLE_BUDGET_TND = 30000.0

# Alerte urgence si le deadline est à ce nombre de jours ou moins
URGENT_DEADLINE_DAYS = 3

# Nombre de jours minimum jugé réaliste pour répondre à un appel d'offres
MIN_FEASIBLE_DEADLINE_DAYS = 5

# Secteurs jugés stratégiques pour OliveSoft (à adapter à la vraie stratégie commerciale)
STRATEGIC_SECTORS = [
    "banque", "bancaire", "finance", "assurance", "santé", "secteur public",
    "gouvernement", "ministère", "télécommunications", "énergie", "éducation",
    "technologie", "digital", "informatique", "logiciel","IT", "Software", "developpement",
]

# Nombre maximal d'allers-retours Rédacteur <-> Relecteur dans le Proposal Crew
MAX_CREW_ITERATIONS = 3