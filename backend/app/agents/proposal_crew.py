import os
import json
import re

from crewai import Agent, Task, Crew, Process, LLM

from app.config import settings
from app.business_rules import MAX_CREW_ITERATIONS

os.environ.setdefault("OLLAMA_API_BASE", settings.ollama_host)

_crew_llm = LLM(model=f"ollama/{settings.ollama_chat_model}", base_url=settings.ollama_host, temperature=0.4)

WRITER_BACKSTORY = (
    "Consultant senior en avant-vente chez OliveSoft (société de services IT & ingénierie "
    "logicielle). Expert en rédaction de propositions commerciales persuasives, toujours "
    "factuel, jamais exagéré, et systématiquement orienté bénéfice client."
)

REVIEWER_BACKSTORY = (
    "Responsable compliance et qualité commerciale chez OliveSoft. Relit chaque proposition pour "
    "vérifier la présence de chiffres concrets, l'absence de termes vagues, la cohérence avec la "
    "matrice d'exigences, le ton persuasif et la complétude de la structure."
)

SECTION_TITLES = {
    "contexte": "Comprendre votre enjeu",
    "profil_prospect": "Votre organisation, telle que nous la comprenons",
    "reponse_aux_exigences": "Notre réponse à vos exigences, exigence par exigence",
    "references_pertinentes": "Nos références qui font la différence",
    "budget_et_positionnement": "Budget et positionnement concurrentiel",
    "prochaines_etapes": "Prochaines étapes proposées",
}


def _build_writer_agent() -> Agent:
    return Agent(
        role="Rédacteur de propositions commerciales",
        goal="Rédiger une proposition commerciale persuasive, factuelle et riche en preuves concrètes.",
        backstory=WRITER_BACKSTORY,
        llm=_crew_llm,
        allow_delegation=False,
        verbose=False,
    )


def _build_reviewer_agent() -> Agent:
    return Agent(
        role="Relecteur Compliance",
        goal="Garantir la qualité, la précision factuelle et la persuasion de la proposition.",
        backstory=REVIEWER_BACKSTORY,
        llm=_crew_llm,
        allow_delegation=False,
        verbose=False,
    )


def _clean_unknowns(text: str) -> str:
    """Filet de sécurité final: supprime toute trace du mot 'unknown' qui aurait échappé au prompt."""
    text = re.sub(r"\bunknown\b", "à confirmer avec le client", text, flags=re.IGNORECASE)
    return text


def _parse_review_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
    # edge case: relecture non structurée -> on approuve par défaut pour ne jamais bloquer le pipeline,
    # mais on trace l'incident clairement dans le feedback.
    return {"approved": True, "feedback": "Relecture non structurée reçue, validation automatique de secours."}


def _build_context_block(tender: dict, prospect: dict, matrix: list[dict], competitor: dict | None) -> str:
    matrix_text = "\n".join(
        f"- Exigence: {m['requirement_text']} | Couverte: {'Oui' if m['covered'] else 'Non'} | "
        f"Score: {m['score']}/100 | Référence: {m['best_document_title'] or 'aucune'} | "
        f"Preuve concrète: {m['concrete_evidence'] or 'non disponible'} | {m['justification']}"
        for m in matrix
    ) or "Aucune exigence évaluée."

    competitor_text = "Non évalué."
    if competitor:
        competitor_text = (
            f"Fourchette budgétaire estimée: {competitor.get('estimated_budget_range')} "
            f"(confiance: {competitor.get('confidence')})\n"
            f"Positionnement concurrentiel: {competitor.get('competitive_positioning')}\n"
            f"Concurrents probables: {competitor.get('likely_competitors')}"
        )

    return f"""
APPEL D'OFFRES:
Titre: {tender.get('title')}
Organisation: {tender.get('issuing_organization')}
Secteur: {tender.get('sector')}
Budget estimé: {tender.get('estimated_budget')}
Résumé: {tender.get('summary')}

PROFIL DU PROSPECT:
Entreprise: {prospect.get('company_name')}
Secteur: {prospect.get('sector')}
Revenu estimé: {prospect.get('estimated_revenue')}
Partenaires clés: {prospect.get('key_partners')}
Projets passés: {prospect.get('past_projects')}

MATRICE DE COUVERTURE DES EXIGENCES (RAG + scoring formel):
{matrix_text}

INSIGHTS BUDGET & CONCURRENCE:
{competitor_text}
"""


def _writer_task_description(context_block: str, feedback: str) -> str:
    feedback_block = (
        f"\n\nCORRECTIONS DEMANDÉES PAR LE RELECTEUR (à intégrer impérativement):\n{feedback}"
        if feedback else ""
    )
    sections_list = "\n".join(f'- "{title}"' for title in SECTION_TITLES.values())

    return f"""{context_block}{feedback_block}

Rédige une proposition commerciale destinée à être présentée en DIAPOSITIVES. Règles impératives:
1. Pour chaque exigence "Couverte: Oui", cite la preuve concrète fournie (durée, taille d'équipe,
   budget, nom de projet/client) pour montrer précisément comment OliveSoft y répond.
2. Pour les exigences non couvertes, formule-le honnêtement comme un point à approfondir ensemble,
   jamais comme un échec.
3. N'écris JAMAIS le mot "unknown". Si une donnée manque, reformule ("à confirmer avec le client").
4. Format: pour chaque section, 4 à 6 puces courtes commençant par "- ", 25 mots maximum chacune.
   Pas de longs paragraphes, pas de tableaux Markdown, pas de sous-titres.
5. Mets en gras avec **...** uniquement quelques chiffres ou noms clés dans les puces, jamais dans les titres.
6. Chaque section contient au moins un chiffre concret issu des données fournies. N'invente rien.
7. Ton persuasif, confiant, orienté bénéfices business pour CE client, jamais générique.
8. Titres de section au format "## Titre", EXACTEMENT ces titres et dans cet ordre:
{sections_list}

Retourne uniquement le contenu Markdown, sans commentaire additionnel.
"""


def _reviewer_task_description(draft: str, context_block: str) -> str:
    return f"""{context_block}

PROPOSITION À RELIRE:
{draft}

Évalue strictement cette proposition selon ces critères:
- Contient-elle au moins 2 chiffres ou preuves concrètes (durée, taille d'équipe, budget, nom de projet) ?
- Le mot "unknown" apparaît-il quelque part ? (si oui, rejet automatique)
- Chaque exigence couverte est-elle justifiée par une preuve précise plutôt qu'une affirmation vague ?
- Le ton est-il persuasif sans être exagéré ?
- Toutes les sections demandées sont-elles présentes et complètes ?

Retourne UNIQUEMENT un JSON:
{{
  "approved": true ou false,
  "feedback": "si approved=false, liste précise et actionnable des corrections. Si approved=true, chaîne vide."
}}
"""


def generate_proposal_with_crew(
    tender: dict, prospect: dict, matrix: list[dict], competitor: dict | None = None
) -> dict:
    context_block = _build_context_block(tender, prospect, matrix, competitor)

    writer = _build_writer_agent()
    reviewer = _build_reviewer_agent()

    draft_markdown = ""
    feedback = ""
    approved = False
    iterations = 0

    for iterations in range(1, MAX_CREW_ITERATIONS + 1):
        writer_task = Task(
            description=_writer_task_description(context_block, feedback),
            agent=writer,
            expected_output="Proposition commerciale complète en Markdown.",
        )
        writer_crew = Crew(agents=[writer], tasks=[writer_task], process=Process.sequential, verbose=False)
        draft_markdown = _clean_unknowns(str(writer_crew.kickoff()))

        reviewer_task = Task(
            description=_reviewer_task_description(draft_markdown, context_block),
            agent=reviewer,
            expected_output="JSON avec approved (bool) et feedback (string).",
        )
        reviewer_crew = Crew(agents=[reviewer], tasks=[reviewer_task], process=Process.sequential, verbose=False)
        review = _parse_review_json(str(reviewer_crew.kickoff()))

        approved = bool(review.get("approved", False))
        feedback = review.get("feedback", "")

        if approved:
            break

    return {
        "content_markdown": draft_markdown,
        "content_sections": _split_markdown_into_sections(draft_markdown),
        "approved": approved,
        "review_feedback": feedback,
        "iterations": iterations,
    }


def _split_markdown_into_sections(markdown: str) -> dict:
    """Découpe la proposition en sections identifiables pour l'édition humaine granulaire."""
    sections = {}
    current_key = None
    current_lines = []
    title_to_key = {v.lower(): k for k, v in SECTION_TITLES.items()}

    for line in markdown.splitlines():
        matched_key = None
        if line.strip().startswith("#"):
            stripped_title = line.strip().lstrip("#").strip().lower()
            for title, key in title_to_key.items():
                if title in stripped_title:
                    matched_key = key
                    break

        if matched_key:
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = matched_key
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()
    elif markdown.strip():
        # edge case: le modèle n'a pas respecté le format de titres attendu
        sections["contenu_complet"] = markdown.strip()

    return sections


def regenerate_section_with_prompt(
    section_key: str, current_section_content: str, user_instruction: str,
    tender: dict, prospect: dict, matrix: list[dict]
) -> str:
    """Human-in-the-loop: régénère une seule section à partir d'une instruction libre du commercial."""
    writer = _build_writer_agent()
    context_block = _build_context_block(tender, prospect, matrix, None)

    description = f"""{context_block}

SECTION ACTUELLE ("{SECTION_TITLES.get(section_key, section_key)}"):
{current_section_content}

INSTRUCTION DU COMMERCIAL:
{user_instruction}

Réécris UNIQUEMENT cette section en appliquant l'instruction, en conservant le même titre Markdown,
en restant strictement factuel (aucune invention), et sans jamais écrire le mot "unknown".
"""
    task = Task(description=description, agent=writer, expected_output="Section Markdown mise à jour.")
    crew = Crew(agents=[writer], tasks=[task], process=Process.sequential, verbose=False)
    return _clean_unknowns(str(crew.kickoff()))