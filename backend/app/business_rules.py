"""
Règles métier de qualification des tenders. Centralisées ici pour pouvoir
être ajustées facilement sans toucher à la logique des services.
"""

# Seuil minimal de couverture pour qu'une exigence individuelle soit "couverte"
COVERAGE_THRESHOLD = 50.0

# Score global minimal pour qu'un tender passe en statut "qualified"
QUALIFICATION_THRESHOLD = 45.0

# Budget plancher en dessous duquel un tender est jugé peu rentable (TND)
MIN_VIABLE_BUDGET_TND = 30000.0

# Alerte urgence si le deadline et à ce nombre de jours ou moins
URGENT_DEADLINE_DAYS = 3

MIN_FEASIBLE_DEADLINE_DAYS = 5

STRATEGIC_SECTORS = [
    "banque", "bancaire", "finance", "assurance", "santé", "secteur public",
    "gouvernement", "ministère", "télécommunications", "énergie", "éducation",
    "technologie", "digital", "informatique", "logiciel", "communication",
    "développement économique", "investissement", "territorial", 
]

# Nombre maximal d'allers-retour Rédacteur <-> Relecteur dans le Proposal Crew
MAX_CREW_ITERATIONS = 3