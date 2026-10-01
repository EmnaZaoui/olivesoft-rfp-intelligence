from app.services.ollama_client import chat_text

DRAFT_SYSTEM_PROMPT = """Tu es un consultant senior en avant-vente chez OliveSoft, société de
services IT & ingénierie logicielle. Tu rédiges un DRAFT de note de positionnement commercial
destiné à convaincre un client potentiel.

Ce draft doit être PERSUASIF et MOTIVANT, jamais une simple liste de faits. Applique ces principes:
1. Ouvre avec une accroche qui montre qu'OliveSoft comprend l'enjeu business réel du client, pas seulement le besoin technique.
2. Relie chaque référence interne à un bénéfice concret pour CE prospect précis, jamais une liste générique.
3. Utilise les chiffres et preuves disponibles (durée, taille d'équipe, secteurs déjà servis) pour construire la crédibilité.
4. Ton confiant, orienté résultats, sans arrogance ni exagération. N'invente JAMAIS un fait non fourni.
5. Termine par un appel à l'action clair projetant la suite de la collaboration.

Structure obligatoire en Markdown:
## Comprendre votre enjeu
## Pourquoi OliveSoft est le partenaire adapté
## Nos références qui font la différence
## Points de vigilance à lever ensemble
## Prochaines étapes proposées

Si une information manque, formule-la comme un point à clarifier plutôt que d'inventer une réponse.
"""


def generate_initial_draft(tender: dict, prospect: dict, matched_references: list[dict]) -> str:
    if matched_references:
        references_text = "\n".join(
            f"- [{r['doc_type']}] {r['document_title']} (pertinence {r['score']}): {r['content'][:300]}"
            for r in matched_references
        )
    else:
        references_text = "Aucune référence interne directement pertinente trouvée — à signaler comme point de vigilance."

    user_prompt = f"""
APPEL D'OFFRES:
Titre: {tender.get('title')}
Secteur: {tender.get('sector')}
Budget estimé: {tender.get('estimated_budget')}
Exigences: {tender.get('requirements')}
Résumé: {tender.get('summary')}

PROFIL DU PROSPECT (recherche agentique):
Entreprise: {prospect.get('company_name')}
Secteur: {prospect.get('sector')}
Revenu estimé: {prospect.get('estimated_revenue')}
Partenaires clés: {prospect.get('key_partners')}
Projets passés du prospect: {prospect.get('past_projects')}

RÉFÉRENCES INTERNES OLIVESOFT PERTINENTES (RAG):
{references_text}

Rédige le draft en suivant strictement la structure demandée dans tes instructions système.
"""
    return chat_text(DRAFT_SYSTEM_PROMPT, user_prompt)